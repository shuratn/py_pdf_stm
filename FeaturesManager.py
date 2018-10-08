import copy
import os
import sys
from pathlib import Path
from typing import List, Dict
import json

from DataSheetManager import DataSheetManager
from FeatureExtractors.MKL_feature_extractor import MKLFeatureListExtractor
from FeatureExtractors.MK_feature_extractor import MKFeatureListExtractor
from FeatureExtractors.SMT32L_feature_extractor import STM32LFeatureListExtractor
from FeatureExtractors.SMT32F_feature_extractor import STM32FFeatureListExtractor
import xlsxwriter


class FeatureManager:
    EXTRACTORS = {
        'STM32L': STM32LFeatureListExtractor,
        'STM32F': STM32FFeatureListExtractor,
        'MKL': MKLFeatureListExtractor,
        'MK': MKFeatureListExtractor,
    }

    cache_path = Path(r'./cache/mcu_cache.json').absolute()

    def __init__(self, datasheets: List[str]):
        with open('config.json', 'r') as fp:
            if not fp.read():
                self.config = {'corrections': {}, 'unify': {}}
            else:
                fp.seek(0)
                self.config = json.load(fp)
        self.datasheets = datasheets
        self.mcs_features = {}
        self.same_features = []
        self.load_cache()
        self.datasheet_manager = DataSheetManager(datasheets)
        

    def get_extractor(self, mc: str):
        for extractor_name in sorted(self.EXTRACTORS, key=lambda l: len(l), reverse=True):
            if extractor_name.upper() in mc.upper():
                return self.EXTRACTORS[extractor_name]

    def parse(self):
        self.datasheet_manager.get_or_download()
        for mc in self.datasheets:
            extractor = self.get_extractor(mc)
            datasheet = self.datasheet_manager[mc]
            if datasheet:
                extractor_obj = extractor(mc, datasheet, self.config)
                extractor_obj.process()
                extractor_obj.unify_names()
                self.mcs_features[extractor_obj.mc_family] = extractor_obj.features
                pass  # handle feature extraction
            else:
                raise Exception('Can\' find {} in database'.format(mc))
        self.save()

    def get_config_name(self,mc):
        for extractor_name in sorted(self.EXTRACTORS, key=lambda l: len(l), reverse=True):
            if extractor_name.upper() in mc.upper():
                return extractor_name
        return None

    def load_cache(self):
        if not self.cache_path.exists():
            self.cache_path.parent.mkdir(exist_ok=True)
            self.mcs_features = {}
            return
        with self.cache_path.open('r+') as fp:
            new = json.load(fp)  # type: Dict
        self.mcs_features.update(new)

    def save(self):
        if self.cache_path.exists():
            with self.cache_path.open('r+') as fp:
                old = json.load(fp)  # type: Dict
            old.update(self.mcs_features)
        with self.cache_path.open('w') as fp:
            json.dump(self.mcs_features, fp,indent=1)

    def collect_same_features(self):
        same_features = set()
        for _, mcs in self.mcs_features.copy().items():
            for mc, features in mcs.items():
                if not same_features:
                    same_features = set(features.keys())
                    continue
                same_features.intersection_update(set(features.keys()))
        print(same_features)
        self.same_features = list(same_features)

    def write_excel_file(self):
        excel = xlsxwriter.Workbook('FeatureList.xlsx')
        sheet = excel.add_worksheet()
        self.collect_same_features()

        # UTIL VARS
        merge_format = excel.add_format({'align': 'center', 'valign': 'center'})
        feature_vertical_offset = 0

        # Writing headers
        sheet.write(0, 0, 'MCU family')
        sheet.write(1, 0, 'MCU')
        name_offset = 0
        sub_name_offset = 1
        mcs_features = copy.deepcopy(self.mcs_features)
        for n, (mc_name, sub_mcs) in enumerate(mcs_features.items()):
            sheet.merge_range(0, 1 + name_offset, 0, 1 + name_offset + len(sub_mcs) - 1, mc_name,
                              cell_format=merge_format)
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
            sheet.write(feature_vertical_offset + n, 0, common_feature)
            mc_offset = 0
            for mc_name, sub_mcs in mcs_features.items():
                sub_mc_offset = 0
                for sub_mc_name, features in sub_mcs.items():
                    if common_feature not in features:
                        continue
                    feature = features.pop(common_feature)
                    if type(feature) == dict:
                        feature = r'/'.join(feature.keys())
                    if type(feature) == list:
                        feature = r'/'.join(feature)
                    sheet.write(n + feature_vertical_offset, 1 + sub_mc_offset + mc_offset, feature)
                    sub_mc_offset += 1
                mc_offset += len(sub_mcs)
        feature_vertical_offset += len(self.same_features)

        excel.close()


if __name__ == '__main__':
    import json

    if len(sys.argv) < 2:
        print('Usage: {} DATASHEET.pdj'.format(os.path.basename(sys.argv[0])))
        exit(0xDEADBEEF)
    controllers = sys.argv[1:]
    feature_manager = FeatureManager(controllers)
    feature_manager.parse()
    feature_manager.write_excel_file()
    with open('features.json', 'w') as fp:
        json.dump(feature_manager.mcs_features, fp, indent=2)
    # KL17P64M48SF6 stm32L451 MK11DN512AVMC5
    a = 5
