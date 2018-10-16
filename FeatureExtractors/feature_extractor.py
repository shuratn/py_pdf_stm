import sys
import traceback
from pprint import pprint
from typing import List, Dict, Any

from DataSheetParsers.DataSheet import DataSheet
from PinManager import PinManager
from TableExtractor import TableExtractor, Table
from Utils import is_numeric, is_dict, remove_units, replace_i, merge


def convert_type(name: str, value):
    if type(value) == str:
        value = value.replace(',', '')
        value = value.strip('\n ')
    if 'KB' in name.upper():
        name = remove_units(name, 'kb')
        if is_numeric(value):
            value = int(value)
    if 'MB' in name.upper():
        name = remove_units(name, 'mb')
        if is_numeric(value):
            value = int(value) * 1024
        elif type(value) == int:
            value *= 1024

    if 'MHZ' in name.upper():
        name = remove_units(name, 'mhz')
        if is_numeric(value):
            value = int(value)

    if type(value) == str:
        if 'KB' in value:
            value = replace_i(value, 'kb', '')
            if is_numeric(value):
                value = int(value)
            elif type(value) == int:
                pass
            else:
                value += 'KB'
            return name, value
        if 'MB' in value:
            value = replace_i(value, 'mb', '')
            if is_numeric(value):
                value = int(value) * 1024
            elif type(value) == int:
                value *= 1024

            else:
                value += 'MB'
            return name, value
        if 'MHZ' in value.upper():
            value = replace_i(value, 'MHz', '')
            if is_numeric(value):
                value = int(value)
            elif type(value) == int:
                pass
            else:
                value += 'MHz'
            return name, value
    # UNIFIED NAMES
    # int_values = ['Flash memory', 'RAM', 'UART', 'SPI', 'Total GPIOS','CPU Frequency']
    # if name in int_values:
    if type(value) != int and is_numeric(value):
        if type(value) == str:
            if not (value.lower() == 'no' or value.lower() == 'yes'):
                try:
                    value = int(value)
                except Exception as ex:
                    print('Failed to convert {} {} to int\n{}'.format(name, value, ex))
    return name, value


class FeatureListExtractor:  # This class is adapted to STM

    def fix_name(self, name):
        name = "".join([part[::-1] for part in name[::1][::-1].split('\n')])
        return self.config['corrections'].get(name, name)

    def __init__(self, controller: str, datasheet: DataSheet, config) -> None:
        """
        Class for comparing multiple STM32 controllers

        :type controller_list: list of stm controllers that you want to compare
        """
        self.controller = controller
        self.config = config  # type: Dict[str,Dict]
        self.datasheet = datasheet
        self.features_tables = []  # type: List[Table]
        self.features = {}  # type: Dict[str,Dict]
        self.pin_data = {}  # type: Dict[str, Dict[str, Any]]
        self.config_name = 'UNKNOWN CONTROLLER'
        self.mc_family = 'UNKNOWN'
        self.pin_manager = PinManager(self.pin_data,{})
        self.post_init()

    def post_init(self):
        pass

    def process(self):
        self.extract_tables()
        self.extract_features()
        del self.features_tables
        self.extract_pinout()
        return self.features

    def extract_table(self, datasheet, page):
        print('Extracting table from {} page'.format(page + 1))
        pdf_int = TableExtractor(str(datasheet.path))
        try:
            table = pdf_int.parse_page(page)
        except Exception as ex:
            pass
            table = None
        return table

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER
        return

    def handle_feature(self, name, value):
        if '\u2013' in name:
            name = name.replace('\u2013', '-')
        if type(value) == str:
            if '\u2013' in value:
                value = value.replace('\u2013', '-')
            if '\n' in value:
                value = value.replace('\n', ' ')

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
                        features = sorted(features, key=lambda cell: cell.center.x)
                        texts = list(map(lambda cell: cell.clean_text, features))
                        controller_features_names.append(' '.join(texts))
                else:
                    texts = list(map(lambda cell: cell.clean_text, table.get_col(0)[1:]))
                    controller_features_names.extend(texts)
                # EXTRACTING STM FEATURES
                current_stm_name = ""
                mcu_counter = {}
                name = 'ERROR'
                for col_id in range(features_cell_span, len(table.get_row(0))):
                    features = table.get_col(col_id)
                    for n, feature in enumerate(features):
                        if n == 0:
                            name = table.get_cell(col_id, 0).clean_text

                            if name == current_stm_name:

                                num = mcu_counter[current_stm_name]
                                name += '-{}'.format(num)
                                mcu_counter[current_stm_name] += 1
                            else:
                                current_stm_name = name
                            if not mcu_counter.get(current_stm_name, False):
                                mcu_counter[current_stm_name] = 1
                            if not controller_features.get(name, False):
                                controller_features[name] = {}
                            continue
                        feature_name = controller_features_names[feature_offset + n - 1]
                        feature_value = feature.text
                        for n, v in self.handle_feature(feature_name, feature_value):
                            if n and v:
                                n, v = convert_type(n, v)
                                if controller_features[name].get(n, False):
                                    v = self.merge_features(controller_features[name].get(n), v)
                                    controller_features[name][n] = v
                                else:
                                    controller_features[name][n] = v
                feature_offset = len(controller_features_names)
            except Exception as ex:
                sys.stderr.write("ERROR {}".format(ex))
                traceback.print_exc()

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

    def extract_pinout(self):

        for package, pin_data in self.pin_data.items():
            for mcu,mcu_features in self.features.items():
                if package in mcu_features.get('PACKAGE',[]):
                    self.features[mcu]['PINOUT']=pin_data
        return self.pin_data

    def unify_names(self):
        unknown_names = {}
        for mc, features in self.features.items():
            unknown_names[mc] = []
            mc_features = self.features[mc].copy()
            mc_features = {k.upper(): v for k, v in mc_features.items()}
            for feature_name, features_value in features.items():
                feature_name = feature_name.upper()
                if features_value:
                    if self.config_name in self.config['unify']:
                        unify_list = self.config['unify'][self.config_name]  # type: Dict[str,str]
                        unify_list = {k.upper(): v.upper() for k, v in unify_list.items()}
                        known = True
                        if feature_name not in unify_list:
                            if feature_name not in unify_list.values():
                                known = False
                                if feature_name not in unknown_names:
                                    unknown_names[mc].append(feature_name)
                        if known:
                            new_name = unify_list.get(feature_name,
                                                      feature_name).upper()  # in case name is already unified
                            values = mc_features.pop(feature_name)
                            new_name, values = convert_type(new_name, values)
                            new_name = new_name.upper()
                            if new_name in mc_features:
                                mc_features[new_name] = self.merge_features(mc_features[new_name],
                                                                            values)
                            else:
                                mc_features[new_name] = values
                        else:
                            new_name = feature_name  # in case name is already unified
                            values = mc_features.pop(feature_name)
                            new_name, values = convert_type(new_name, values)
                            mc_features[new_name.upper()] = values

                    else:
                        unknown_names[mc].append(feature_name)

            self.features[mc] = mc_features
        for mc, features in unknown_names.items():
            unknown_names = list(set(features))
            if unknown_names:
                print('List of unknown features for', mc)
                print('Add correction if name is mangled')
                print('Or add unify for this feature')
                for unknown_feature in unknown_names:
                    print('\t', unknown_feature)
                print('=' * 20)
                print()



    @staticmethod
    def merge_features(old, new):
        return merge(old, new)


if __name__ == '__main__':
    datasheet = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\stm32L\STM32L476.pdf")
    feature_extractor = FeatureListExtractor('STM32L476', datasheet, {})
    feature_extractor.process()
    pprint(feature_extractor.features)
