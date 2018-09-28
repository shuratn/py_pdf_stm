import os
import sys
from typing import List
from SMT32_feature_extractor import STM32FeatureListExtractor


class FeatureManager:
    EXTRACTORS = {'STM32': STM32FeatureListExtractor}

    def __init__(self, microcontrollers: List[str]):
        self.mcs = microcontrollers
        self.mcs_features = {}

    def parse(self):
        for extractor_name, extractor in self.EXTRACTORS.items():
            for mc in self.mcs:
                if extractor_name.upper() in mc.upper():
                    features = extractor(mc).process()
                    self.mcs_features[mc] = features
                    pass  # handle feature extraction


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: {} DATASHEET.pdj'.format(os.path.basename(sys.argv[0])))
        exit(0xDEADBEEF)
    controllers = sys.argv[1:]
    feature_manager = FeatureManager(controllers)
    feature_manager.parse()
    a = 5
