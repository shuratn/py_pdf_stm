import copy
import json
import sys
import traceback
from pathlib import Path
from typing import Dict, Any

import xlsxwriter

from FeaturesManager import FeatureManager
from FeatureExtractors.feature_extractor import convert_type
from Utils import *


class MCUHelper:

    def __init__(self, feature_list: str):
        self.matching = {}
        with open(feature_list) as fp:
            self.required_feature = json.load(fp)  # type: Dict[str,Any]
        controllers = sys.argv[2:]
        self.feature_manager = FeatureManager(controllers)
        # feature_manager.parse()
        self.mcu_features = self.feature_manager.mcs_features

    def match(self, required_value, feature_value, cmp_type, ):
        mismatch = False
        if cmp_type == '>':
            if not feature_value >= required_value:
                mismatch = True
        elif cmp_type == '<':
            if not feature_value <= required_value:
                mismatch = True
        elif cmp_type == '=':
            if not feature_value == required_value:
                mismatch = True
        else:
            if not feature_value >= required_value:
                mismatch = True
        return not mismatch

    def get_cmp_type(self, name):
        if name[-1] in '<>=':
            feature_name = name[:-1]
            cmp_type = name[-1]
        else:
            feature_name = name
            cmp_type = '>'
        return feature_name, cmp_type

    def compare(self, req_name, req_value, feature_name, feature_value):
        match = False
        req_name, cmp_type = self.get_cmp_type(req_name)
        if req_name != feature_name:
            if req_name != 'ANY':
                return None
        if is_dict(req_value) and is_dict(feature_value):
            for rk, rv in req_value.items():
                for fk, fv in feature_value.items():
                    ret = self.compare(rk, rv, fk, fv)
                    if ret is not None:
                        if ret:
                            match = True
            return match
        if is_int(req_value) and is_int(feature_value):
            return self.match(req_value, feature_value, cmp_type)
        if is_str(req_value) or is_str(feature_value):
            print('STRINGS ARE NOT SUPPORTED YET')
            return None

    def collect_matching(self):
        self.print_user_req()
        print('Searching for matching microcontrolers!')
        for mcu_family, mcus in self.mcu_features.items():
            for mcu_name, mcu_features in mcus.items():
                matched = True
                for req_name, req_value in self.required_feature.items():
                    req_feature, cmp_type = self.get_cmp_type(req_name)
                    feature_value = mcu_features.get(req_feature, None)
                    if feature_value:
                        try:
                            if is_dict(req_value) and is_dict(feature_value):
                                matched &= self.compare(req_name, req_value, req_name, feature_value)
                            else:
                                matched &= self.match(req_value, feature_value, cmp_type)

                        except Exception as ex:
                            matched = False
                            print('ERROR:', ex)
                            print('INFO:', req_name, ':', req_value)
                            print('INFO2:', mcu_name, ':', feature_value)
                            traceback.print_exc()
                    else:
                        matched = False
                if matched:
                    self.matching[mcu_name] = mcu_features

        print('Found {} matching'.format(len(self.matching)))
        print('Matching microcontrolers:')
        if not self.matching:
            print('No matches')
        else:
            self.print_matching()

        return self

    def print_matching(self):
        for match_name, match_features in self.matching.items():
            print('\t', match_name)
            # for feature, value in match_features.items():
            #     print('\t', feature, ':', value)

    def print_user_req(self):
        print('Your requirements are:')
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
        # print(same_features)
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
                if mc_features.get(common_feature, False):
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
        for m, mc_features in enumerate(matching.values()):  # type: int,dict
            row = ''
            count = 0
            row_offset_sub = 0
            for feature, value in mc_features.items():
                row += str(feature) + ' : ' + str(value) + '\n'
                count += 1
                if count > 10:
                    sheet.write(row_offset + row_offset_sub, 1 + m, row, wraps)
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
    for mc_family_name, mc_family in feature_manager.mcs_features.items():
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
    feature_manager.save()


if __name__ == '__main__':
    known_commands = ['parse', 'download', 'dump_cache']
    if len(sys.argv) > 1:
        if sys.argv[1] == 'parse':
            parse_all()
            exit(0xDEADBEEF)
        elif sys.argv[1] == 'download':
            feature_manager = FeatureManager(sys.argv[2:])
            feature_manager.parse()
            exit(0xDEADCAFE)
        elif sys.argv[1] == 're-unify':
            reunify_cache()
            exit(0xBEEFCAFE)
        elif sys.argv[1] == 'dump_cache':
            feature_manager = FeatureManager([])
            with open('./dump.txt', 'w') as fp:
                print('DUMPING ALL KNOWN MCU\'s')
                for family_name, family_mcus in feature_manager.mcs_features.items():
                    fp.write(family_name + ' :\n')
                    print(family_name, ':')
                    for mcu_name in family_mcus.keys():
                        fp.write('\t' + mcu_name + '\n')
                        print('\t', mcu_name)

        elif sys.argv[1] == 'filter':
            MCUHelper(sys.argv[1]).collect_matching().write_excel()

    else:
        print('USSAGE: {} [{}]'.format(sys.argv[0], '|'.join(known_commands)))
        print('\tdownload [MCU NAME HERE] - downloads and parses new datasheet')
        print('\tdump_cache - prints all MCUs in cache')
        print('\tre-unify - tries to re-unify everything')
        print('\tparse - re-parses all datasheets')
