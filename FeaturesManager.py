import os
import sys
from typing import List

from DataSheetManager import DataSheetManager
from KL_feature_extractor import KLFeatureListExtractor
from MK_feature_extractor import MKFeatureListExtractor
from SMT32_feature_extractor import STM32FeatureListExtractor


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


if __name__ == '__main__':
    import json

    if len(sys.argv) < 2:
        print('Usage: {} DATASHEET.pdj'.format(os.path.basename(sys.argv[0])))
        exit(0xDEADBEEF)
    controllers = sys.argv[1:]
    feature_manager = FeatureManager(controllers)
    feature_manager.parse()
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
