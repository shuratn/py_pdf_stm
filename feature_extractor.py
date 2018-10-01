import os
import sys
from pprint import pprint
from typing import List, Dict

from DataSheet import DataSheet
from PDFInterpreter import PDFInterpreter, Table


def fetch_from_all(lists, num):
    return [arr[num] for arr in lists]


class FeatureListExtractor:  # This class is adapted to STM

    KNOWN_NAMES = {
        'Flash memory':'ROM',
    }

    def __init__(self, controller:str,datasheet:DataSheet):
        """
        Class for comparing multiple STM32 controllers

        :type controller_list: list of stm controllers that you want to compare
        """
        self.controller = controller
        self.datasheet = datasheet
        self.features_tables = []  # type: List[Table]
        self.features = {}

    def process(self):
        self.extract_tables()
        self.extract_features()
        return self.features



    @staticmethod
    def extract_table(datasheet, page):
        print('Extracting table from {} page'.format(page + 1))
        pdf_int = PDFInterpreter(str(datasheet.path))
        table = pdf_int.parse_page(page)
        return table

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER
        return

    def handle_feature(self, name, value):
        return [(name, value)]  # Can be list of values and names

    def extract_features(self):
        controller_features_names = []
        controller_features = {}
        feature_offset = 0
        for table in self.features_tables:
            try:
                if not table.global_map:
                    continue
                _, features_cell_span = table.get_cell_span(table.get_col(0)[0])
                # EXTRACTING NAMES OF FEATURES
                if features_cell_span > 1:
                    for row_id, row in table.global_map.items():
                        if row_id == 0:
                            continue
                        features = set(list(row.values())[:features_cell_span])
                        texts = list(map(lambda cell: cell.clean_text, features))
                        controller_features_names.append(' '.join(texts))
                else:
                    texts = list(map(lambda cell: cell.clean_text, table.get_col(0)[1:]))
                    controller_features_names.extend(texts)
                # EXTRACTING STM FEATURES
                current_stm_name = ""
                for col_id in range(features_cell_span, len(table.get_row(0))):
                    features = table.get_col(col_id)
                    for n, feature in enumerate(features):
                        if n == 0:
                            name = table.get_cell(col_id, 0).clean_text
                            if name == current_stm_name:
                                name += '-{}'.format(col_id - features_cell_span)
                            current_stm_name = name
                            if not controller_features.get(current_stm_name, False):
                                controller_features[current_stm_name] = {}
                            continue
                        feature_name = controller_features_names[feature_offset + n - 1]
                        feature_value = feature.text
                        for n,v in self.handle_feature(feature_name,feature_value):
                            controller_features[current_stm_name][n] = v
                feature_offset = len(controller_features_names)
            except:
                continue

        # FILL MISSING FIELDS
        for stm_name in controller_features.keys():
            for stm_name2 in controller_features.keys():
                if stm_name == stm_name2:
                    continue
                if stm_name in stm_name2:
                    for feature_name, value in controller_features[stm_name].items():
                        if controller_features[stm_name2].get(feature_name, False):
                            continue
                        else:
                            controller_features[stm_name2][feature_name] = value

        controller_features = self.unify_names(controller_features)

        self.features = controller_features
        return controller_features

    def unify_names(self, controller_features): # OVERRIDE IN SUBCLASS
        return controller_features


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: {} DATASHEET.pdj'.format(os.path.basename(sys.argv[0])))
        exit(0xDEADBEEF)
    controllers = sys.argv[1]
    feature_extractor = FeatureListExtractor(controllers)
    feature_extractor.process()
    pprint(feature_extractor.features)
