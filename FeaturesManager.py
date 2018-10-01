import os
import sys
from typing import List

from DataSheetManager import DataSheetManager
from SMT32_feature_extractor import STM32FeatureListExtractor


class FeatureManager:
    EXTRACTORS = {'STM32': STM32FeatureListExtractor}

    def __init__(self, microcontrollers: List[str]):
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
                        features = extractor(mc,datasheet).process()
                        self.mcs_features[mc] = features
                        pass  # handle feature extraction
                    else:
                        raise Exception('Can\' find {} in database'.format(mc))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: {} DATASHEET.pdj'.format(os.path.basename(sys.argv[0])))
        exit(0xDEADBEEF)
    controllers = sys.argv[1:]
    feature_manager = FeatureManager(controllers)
    feature_manager.parse()
    a = 5
