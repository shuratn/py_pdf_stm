import os
import sys
from pprint import pprint
from typing import List, Dict

from DumpPDFText import DataSheet
from PDFInterpreter import PDFInterpreter, Table


def fetch_from_all(lists, num):
    return [arr[num] for arr in lists]


class STM32FeaturesList:

    def __init__(self, stms: List[str]):
        """
        Class for comparing multiple STM32 controllers

        :type stms: list of stm controllers that you want to compare
        """
        self.stms = stms
        self.stm_datasheets = {}  # type: Dict[DataSheet]
        self.stm_features_tables = {}  # type: Dict[List[Table]]
        self.stm_features = {}

    def gather_datasheets(self):
        for stm in self.stms:
            datasheet = DataSheet(stm)
            self.stm_datasheets[stm] = datasheet

    @staticmethod
    def extract_table(datasheet, page):
        print('Extracting table from {} page'.format(page + 1))
        pdf_int = PDFInterpreter(pdf_file=datasheet.pdf_file, page=page)
        pdf_int.flip_page = True
        pdf_int.process()
        return pdf_int.table

    def extract_tables(self):
        for stm in self.stms:
            print('Extracting tables for', stm)
            datasheet = self.stm_datasheets[stm]

            table_pt1 = self.extract_table(datasheet, 12)
            table_pt2 = self.extract_table(datasheet, 13)
            table_pt3 = self.extract_table(datasheet, 14)
            self.stm_features_tables[stm] = [table_pt1, table_pt2, table_pt3]

    def extract_features(self):
        stm_features_names = []
        stm_features = {}
        multiple_with_same_name = True
        for stm in self.stms:
            t1, t2, t3 = self.stm_features_tables[stm]  # type: Table,Table,Table
            feature_offset = 0
            for table in [t1, t2, t3]:
                if not table.global_map:
                    continue
                _, features_cell_span = table.get_cell_span(table.get_col(0)[0])
                # EXTRACTING NAMES OF FEATURES
                if features_cell_span > 1:
                    for row_id,row in table.global_map.items():
                        if row_id==0:
                            continue
                        features = set(list(row.values())[:features_cell_span])
                        texts = list(map(lambda cell: cell.clean_text, features))
                        stm_features_names.append(' '.join(texts))
                else:
                    texts = list(map(lambda cell: cell.clean_text, table.get_col(0)[1:]))
                    stm_features_names.extend(texts)
                # EXTRACTING STM FEATURES
                current_stm_name = ""
                for col_id in range(features_cell_span, len(table.get_row(0))):
                    features = table.get_col(col_id)
                    for n, feature in enumerate(features):
                        if n == 0:
                            name = table.get_cell(col_id, 0).clean_text
                            if name == current_stm_name:
                                name += '-{}'.format(col_id-features_cell_span)
                            current_stm_name = name
                            if not stm_features.get(current_stm_name,False):
                                stm_features[current_stm_name] = {}
                            continue
                        feature_name = stm_features_names[feature_offset + n-1]
                        feature_value = feature.clean_text
                        stm_features[current_stm_name][feature_name] = feature_value

                feature_offset = len(stm_features_names)

        # FILL MISSING FIELDS
        for stm_name in stm_features.keys():
            for stm_name2 in stm_features.keys():
                if stm_name == stm_name2:
                    continue
                if stm_name in stm_name2:
                    for feature_name, value in stm_features[stm_name].items():
                        if stm_features[stm_name2].get(feature_name, False):
                            continue
                        else:
                            stm_features[stm_name2][feature_name] = value

        return stm_features


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: {} DATASHEET.pdj'.format(os.path.basename(sys.argv[0])))
        exit(0)
    controllers = sys.argv[1:]
    datasheet = STM32FeaturesList(controllers)
    datasheet.gather_datasheets()
    datasheet.extract_tables()
    features = datasheet.extract_features()
    print(features)
