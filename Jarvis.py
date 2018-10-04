import json
import sys
from pathlib import Path
from pprint import pprint
from typing import Dict, Any

from FeaturesManager import FeatureManager


class MCUHelper:

    def __init__(self, feature_list: str):
        with open(feature_list) as fp:
            self.required_feature = json.load(fp)  # type: Dict[str,Any]
        controllers = sys.argv[2:]
        feature_manager = FeatureManager(controllers)
        # feature_manager.parse()
        self.mcu_features = feature_manager.mcs_features

    def collect_matching(self):
        matching = {}

        for mcu_family, mcus in self.mcu_features.items():
            for mcu_name, mcu_features in mcus.items():
                mismatch = False
                for req, req_value in self.required_feature.items():
                    if req[-1] in '<>=':
                        feature_value = mcu_features.get(req[:-1], None)
                    else:
                        feature_value = mcu_features.get(req, None)
                    if feature_value:
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
                    else:
                        continue
                if not mismatch:
                    matching[mcu_name] = mcu_features
        self.print_user_req()
        print('Matching microcontrolers:')
        if not matching:
            print('No matches')
        else:
            self.print_matching(matching)

    def print_matching(self, matching):
        for match_name, match_features in matching.items():
            print(match_name)
            for feature, value in match_features.items():
                print('\t', feature, ':', value)

    def print_user_req(self):
        print('Your requirements were:')
        for req_name, req_value in self.required_feature.items():
            if req_name[-1] in '<>=':
                cmp_type = req_name[-1]
                req_name = req_name[:-1]
            else:
                cmp_type = '>'
            print('\t', req_name, cmp_type, req_value)


datasheets_path = Path('./datasheets/').absolute()


def parse_all():
    to_parse = []
    for folder in datasheets_path.iterdir():
        if folder.is_dir():
            for ds in folder.iterdir():
                if ds.is_file():
                    to_parse.append(ds.stem)
    FeatureManager(to_parse).parse()


if __name__ == '__main__':
    if sys.argv[1] == 'parse':
        parse_all()
        exit(0xDEADBEEF)
    MCUHelper(sys.argv[1]).collect_matching()
