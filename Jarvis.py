import copy
import json
import sys
import traceback
from pathlib import Path
from typing import Dict, Any

import xlsxwriter

from FeaturesManager import FeatureManager
from feature_extractor import convert_type


class MCUHelper:

    def __init__(self, feature_list: str):
        self.matching = {}
        with open(feature_list) as fp:
            self.required_feature = json.load(fp)  # type: Dict[str,Any]
        controllers = sys.argv[2:]
        self.feature_manager = FeatureManager(controllers)
        # feature_manager.parse()
        self.mcu_features = self.feature_manager.mcs_features

    def collect_matching(self):

        for mcu_family, mcus in self.mcu_features.items():
            for mcu_name, mcu_features in mcus.items():
                mismatch = False
                for req, req_value in self.required_feature.items():
                    if req[-1] in '<>=':
                        feature_value = mcu_features.get(req[:-1], None)
                    else:
                        feature_value = mcu_features.get(req, None)
                    if feature_value:
                        try:
                            if req.endswith('>'):
                                if not feature_value >= req_value:
                                    mismatch = True
                                    break
                            elif req.endswith('<'):
                                if not feature_value <= req_value:
                                    mismatch = True
                                    break
                            elif req.endswith('='):
                                if not feature_value == req_value:
                                    mismatch = True
                                    break
                            else:
                                if not mcu_features[req] > req_value:
                                    mismatch = True
                                    break
                        except Exception as ex:
                            mismatch = True
                            print('ERROR:', ex)
                            print('INFO:', req, ':', req_value)
                            print('INFO2:', mcu_name, ':', feature_value)
                            traceback.print_exc()
                    else:
                        continue
                if not mismatch:
                    self.matching[mcu_name] = mcu_features
        self.print_user_req()
        print('Matching microcontrolers:')
        if not self.matching:
            print('No matches')
        else:
            self.print_matching()

        return self

    def print_matching(self):
        for match_name, match_features in self.matching.items():
            print(match_name)
            # for feature, value in match_features.items():
            #     print('\t', feature, ':', value)

    def print_user_req(self):
        print('Your requirements were:')
        for req_name, req_value in self.required_feature.items():
            if req_name[-1] in '<>=':
                cmp_type = req_name[-1]
                req_name = req_name[:-1]
            else:
                cmp_type = '>'
            print('\t', req_name, cmp_type, req_value)

    def get_common(self):
        same_features = set()
        for mc, features in self.matching.copy().items():
            if not same_features:
                same_features = set(features.keys())
                continue
            same_features.intersection_update(set(features.keys()))
        print(same_features)
        return same_features

    def write_excel(self):
        same_features = self.get_common()
        excel = xlsxwriter.Workbook('Results.xlsx')
        sheet = excel.add_worksheet()

        middle = excel.add_format({'align': 'center', 'valign': 'center'})
        wraps = excel.add_format({'valign': 'top'})
        wraps.set_text_wrap()
        # Writing headers
        sheet.write(0, 0, 'MCU:')

        matching = copy.deepcopy(self.matching)
        for n, mc_name in enumerate(matching.keys()):
            sheet.write(0, 1 + n, mc_name, middle)
            sheet.set_column(0, 1 + n, width=len(mc_name) + 3)
        row_offset = 0
        for n, common_feature in enumerate(same_features):
            sheet.write(1 + n, 0, common_feature)
            for m, mc_features in enumerate(matching.values()):  # type: int,dict
                if mc_features.get(common_feature,False):
                    feature_value = mc_features.pop(common_feature)
                    if type(feature_value) is list:
                        feature_value = '/'.join(feature_value)
                    if type(feature_value) is dict:
                        feature_value = str(feature_value)
                    sheet.write(1 + n, 1 + m, feature_value)
                else:
                    sheet.write(1 + n, 1 + m, 'ERROR MISSING')
            row_offset = n + 1

        row_offset += 1
        sheet.write(row_offset, 0, 'OTHER')
        #TODO: обрабатывать корпуса как фичи
        for m, mc_features in enumerate(matching.values()):  # type: int,dict
            row = ''
            count = 0
            row_offset_sub = 0
            for feature, value in mc_features.items():
                row += str(feature) + ' : ' + str(value) + '\n'
                count += 1
                if count > 10:
                    sheet.write(row_offset+row_offset_sub, 1 + m, row, wraps)
                    row_offset_sub = +1
                    count = 0
                    row = ''

        excel.close()


datasheets_path = Path('./datasheets/').absolute()


def parse_all():
    to_parse = []
    if datasheets_path.exists():
        for folder in datasheets_path.iterdir():
            if folder.is_dir():
                for ds in folder.iterdir():
                    if ds.is_file():
                        to_parse.append(ds.stem)
        FeatureManager(to_parse).parse()
    else:
        print('NO DATASHEETS FOUND')

def reunify_cache():
    feature_manager = FeatureManager([])
    feature_manager.load_cache()
    for mc_family_name,mc_family in feature_manager.mcs_features.items():
        unknown_names = []
        for mc, features in mc_family.items():

            # print(mc)
            mc_features = feature_manager.mcs_features[mc_family_name][mc].copy()
            config_name = feature_manager.get_config_name(mc)
            for feature_name, features_value in features.items():
                if features_value:
                    if config_name in feature_manager.config['unify']:
                        unify_list = feature_manager.config['unify'][config_name]
                        known = True
                        if feature_name not in unify_list:
                            if feature_name not in list(unify_list.values()):
                                known = False
                                if feature_name not in unknown_names:
                                    unknown_names.append(feature_name)
                        if known:
                            new_name = unify_list.get(feature_name, feature_name)  # in case name is already unified
                            values = mc_features.pop(feature_name)
                            new_name, values = convert_type(new_name, values)
                            mc_features[new_name] = values
                    else:
                        unknown_names.append(feature_name)

            feature_manager.mcs_features[mc_family_name][mc] = mc_features
        unknown_names = list(set(unknown_names))
        print('List of unknown features for', mc_family_name)
        print('Add correction if name is mangled')
        print('Or add unify for this feature')
        for unknown_feature in unknown_names:
            print('\t', unknown_feature)
        print('=' * 20)

if __name__ == '__main__':
    if sys.argv[1] == 'parse':
        parse_all()
        exit(0xDEADBEEF)
    if sys.argv[1] == 'download':
        feature_manager = FeatureManager(sys.argv[2:])
        feature_manager.parse()
        exit(0xDEADCAFE)
    if sys.argv[1] == 're-unify':
        reunify_cache()
        exit(0xBEEFCAFE)

    MCUHelper(sys.argv[1]).collect_matching().write_excel()
