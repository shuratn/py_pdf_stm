import os
import sys
from pprint import pprint
from typing import List, Dict

from DataSheet import DataSheet
from KL_DataSheet import KL_DataSheet
from PDFInterpreter import PDFInterpreter, Table


def fetch_from_all(lists, num):
    return [arr[num] for arr in lists]


class FeatureListExtractor:  # This class is adapted to STM

    KNOWN_NAMES = {
        'Flash memory': 'ROM',
    }

    def __init__(self, controller: str, datasheet: DataSheet, config):
        """
        Class for comparing multiple STM32 controllers

        :type controller_list: list of stm controllers that you want to compare
        """
        self.controller = controller
        self.config = config  # type: Dict[str,Dict]
        self.datasheet = datasheet
        self.features_tables = []  # type: List[Table]
        self.features = {} # type: Dict[str,Dict]
        self.mc_family = 'UNKNOWN CONTROLLER'

    def process(self):
        self.extract_tables()
        self.extract_features()
        return self.features

    def extract_table(self, datasheet, page):
        print('Extracting table from {} page'.format(page + 1))
        pdf_int = PDFInterpreter(str(datasheet.path))
        table = pdf_int.parse_page(page)
        return table

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER
        return

    def handle_feature(self, name, value):
        if name in self.config['corrections']:
            name = self.config['corrections'][name]
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
                        for n, v in self.handle_feature(feature_name, feature_value):
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

        self.features = controller_features
        return controller_features

    def unify_names(self):
        unknown_names = []
        for mc, features in self.features.items():
            # print(mc)

            for feature_name,features_value in features.items():
                if feature_name not in self.config['unify']:
                    if feature_name not in list(self.config['unify'].values()):
                        if feature_name not in unknown_names:
                            unknown_names.append(feature_name)
                else:
                    new_name = self.config['unify'][feature_name]
                    values = self.features[mc].pop(feature_name)
                    self.features[mc][new_name] = values
        print('List of unknown features for', self.mc_family)
        print('Add correction if name is mangled')
        print('Or add unify for this feature')
        for unknown_feature in unknown_names:

            print('\t',unknown_feature)
        print('='*20)


if __name__ == '__main__':
    datasheet = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\stm32\stm32L476\stm32L476_ds.pdf")
    feature_extractor = FeatureListExtractor('stm32L476',datasheet,{})
    feature_extractor.process()
    pprint(feature_extractor.features)
