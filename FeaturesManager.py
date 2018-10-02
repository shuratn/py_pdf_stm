import os
import sys
from typing import List

from DataSheetManager import DataSheetManager
from KL_feature_extractor import KLFeatureListExtractor
from MK_feature_extractor import MKFeatureListExtractor
from SMT32_feature_extractor import STM32FeatureListExtractor
import xlsxwriter


class FeatureManager:
    EXTRACTORS = {
        'STM32': STM32FeatureListExtractor,
        'KL': KLFeatureListExtractor,
        'MK': MKFeatureListExtractor,
    }

    def __init__(self, microcontrollers: List[str]):
        with open('config.json', 'r') as fp:
            if not fp.read():
                self.config = {'corrections': {}, 'unify': {}}
            else:
                fp.seek(0)
                self.config = json.load(fp)
        self.datasheet_manager = DataSheetManager(microcontrollers)
        self.mcs = microcontrollers
        self.mcs_features = {}
        self.same_features = []
        self.excel = xlsxwriter.Workbook('FeatureList.xlsx')
        self.sheet = self.excel.add_worksheet()

    def parse(self):
        self.datasheet_manager.get_or_download()
        for extractor_name, extractor in self.EXTRACTORS.items():
            for mc in self.mcs:
                if extractor_name.upper() in mc.upper():
                    datasheet = self.datasheet_manager[mc]
                    if datasheet:
                        extractor_obj = extractor(mc, datasheet, self.config)
                        extractor_obj.process()
                        extractor_obj.unify_names()
                        self.mcs_features[mc] = extractor_obj.features
                        pass  # handle feature extraction
                    else:
                        raise Exception('Can\' find {} in database'.format(mc))

    def collect_same_features(self):
        same_features = set()
        for _, mcs in self.mcs_features.items():
            for mc, features in mcs.items():
                if not same_features:
                    same_features = set(features.keys())
                    continue
                same_features.intersection_update(set(features.keys()))
        print(same_features)
        self.same_features = list(same_features)

    def write_excel_file(self):
        self.collect_same_features()

        # UTIL VARS
        merge_format = self.excel.add_format({'align': 'center', 'valign': 'center'})
        feature_vertical_offset = 0

        # Writing headers
        sheet = self.sheet
        sheet.write(0, 0, 'MCU family')
        sheet.write(1, 0, 'MCU')
        name_offset = 0
        sub_name_offset = 1
        for n, (mc_name, sub_mcs) in enumerate(self.mcs_features.items()):
            sheet.merge_range(0, 1+name_offset, 0, 1+name_offset + len(sub_mcs)-1, mc_name, cell_format=merge_format)
            for sub_mc_name in sub_mcs.keys():
                sheet.write(1, sub_name_offset, sub_mc_name)
                sheet.set_column(sub_name_offset, sub_name_offset, width=len(sub_mc_name) + 3)
                sub_name_offset += 1
            name_offset += len(sub_mcs)
        feature_vertical_offset += 2

        # Writing common features
        mc_offset = 0
        sub_mc_offset = 0
        for n, common_feature in enumerate(self.same_features):
            sheet.write(feature_vertical_offset+n, 0, common_feature)
            mc_offset = 0
            for mc_name, sub_mcs in self.mcs_features.items():
                sub_mc_offset = 0
                for sub_mc_name, features in sub_mcs.items():
                    feature = features.pop(common_feature)
                    if type(feature) == dict:
                        feature = '/'.join(feature.values())
                    # print(feature)
                    sheet.write(n + feature_vertical_offset, 1+sub_mc_offset + mc_offset, feature)
                    sub_mc_offset += 1
                mc_offset += len(sub_mcs)
        feature_vertical_offset += len(self.same_features)

        self.excel.close()


if __name__ == '__main__':
    import json

    if len(sys.argv) < 2:
        print('Usage: {} DATASHEET.pdj'.format(os.path.basename(sys.argv[0])))
        exit(0xDEADBEEF)
    controllers = sys.argv[1:]
    feature_manager = FeatureManager(controllers)
    feature_manager.parse()
    feature_manager.write_excel_file()
    temp = {}
    for mc, features in feature_manager.mcs_features.items():
        try:
            nn = list(features.keys())[0]
            print(nn)
            temp[mc] = list(features[nn].keys())
        except:
            print(mc, features)
    with open('features.json', 'w') as fp:
        json.dump(temp, fp, indent=2)
    # KL17P64M48SF6 stm32L451 MK11DN512AVMC5
    a = 5
