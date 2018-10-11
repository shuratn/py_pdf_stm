import json
import sys
import traceback
from pprint import pprint

from DataSheetParsers.DataSheet import DataSheet
from Utils import *
from FeatureExtractors.feature_extractor import FeatureListExtractor, remove_units, convert_type


class STM32LFeatureListExtractor(FeatureListExtractor):

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER
        print('Extracting tables for', self.controller)
        datasheet = self.datasheet
        self.config_name = 'STM32L'

        table_page = datasheet.table_root.childs[1].page
        page_num = datasheet.get_page_num(table_page)
        table_pt1 = self.extract_table(datasheet, page_num)
        table_pt2 = self.extract_table(datasheet, page_num + 1)
        table_pt3 = self.extract_table(datasheet, page_num + 2)
        if table_pt1:
            self.features_tables.append(table_pt1[0])
        if table_pt2:
            self.features_tables.append(table_pt2[0])
        if table_pt3:
            self.features_tables.append(table_pt3[0])

    def post_init(self):
        self.mc_family = self.controller[:6].upper()  # STM32L451

    def handle_feature(self, name, value):
        value = remove_parentheses(value)
        if name in self.config['corrections']:
            name = self.config['corrections'][name]
        if 'USART' in name or 'LPUART' in name or 'LPUART' in name:
            values = sum(map(int, value.split('\n')))
            return [('UART', values)]
        if 'GPIOs' in name and 'Wakeup' in name:
            values = value.split('\n')
            if 'or' in values[0]:
                values[0] = values[0].split('or')[0]
            if '(' in values[0]:
                values[0] = values[0][:values[0].index('(')]
            return [('GPIOs', int(values[0])), ('Wakeup pins', int(values[1]))]
        if 'ADC' in name and 'Number' in name:
            adc_type = re.findall('(\d+)-bit\s?\w*\sADC\s?\w*', name)[0]
            values = value.split('\n')
            return [('ADC', {'{}-bit'.format(adc_type): {'count': int(values[0]), 'channels': int(values[1])}})]
        if 'Operating voltage' in name:
            value = remove_units(value, 'v')
            values = value.split('to')
            values = list(map(float, values))
            return [('Operating voltage', {'min': values[0], 'max': values[1]})]

        if 'Packages' in name:
            values = re.split('(\D+\s?\d{1,3})', value)
            return [(fucking_replace(name, '\n ', ''), 'Yes') for name in values]

        if 'Operating temperature' in name:
            # -40 to 85 °C / -40 to 125 °C
            value = value.split('\n')[1]
            lo, hi = re.findall(r'(-?\d+)\sto\s(-?\d+)\s', value, re.IGNORECASE)[0]
            return [('Operating temperature', {'min': int(lo), 'max': int(hi)})]

        # if 'timer' in name.lower():
        #     print(value)

        try:
            return super().handle_feature(name, value)
        except:
            return [(name, value)]

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
                            name = name.replace(' ', '').strip()

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
                                _, v = convert_type(n, v)
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


if __name__ == '__main__':
    datasheet = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\stm32L\STM32L451.pdf")
    with open('./../config.json') as fp:
        config = json.load(fp)
    feature_extractor = STM32LFeatureListExtractor('stm32L476', datasheet, config)
    feature_extractor.process()
    pprint(feature_extractor.features)
