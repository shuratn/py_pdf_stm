import json
import sys
import traceback
from pprint import pprint

import pdfplumber
from tqdm import tqdm

from DataSheetParsers.DataSheet import DataSheet
from FeatureExtractors.SMT32L_feature_extractor import STM32LFeatureListExtractor
from Utils import *
from FeatureExtractors.feature_extractor import FeatureListExtractor, remove_units, convert_type


class STM32FFeatureListExtractor(STM32LFeatureListExtractor):

    def __init__(self, controller: str, datasheet: DataSheet, config) -> None:
        self.adc_count_found = False
        self.dac_count_found = False
        super().__init__(controller, datasheet, config)

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER
        print('Extracting tables for', self.controller)
        datasheet = self.datasheet
        self.config_name = 'STM32F'
        table_page = None
        for table in datasheet.table_root.childs:
            if 'features and peripheral' in table.name.lower():
                table_page = table.page
        if table_page is None:
            table_page = datasheet.fallback_table.page
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
            if '\n' in value:
                values = sum(map(int, value.split('\n')))
            elif '/' in value:
                values = sum(map(int, value.split('/')))
            else:
                return [(None, None)]
            return [('UART', values)]
        if 'GPIOs' in name and 'Wakeup' in name:
            values = value.split('\n')
            if 'or' in values[0]:
                values[0] = values[0].split('or')[0]
            if '(' in values[0]:
                values[0] = values[0][:values[0].index('(')]
            return [('GPIOs', int(values[0])), ('Wakeup pins', int(values[1]))]
        if 'ADC' in name:
            adc_type = re.findall('(\d+)-bit\s?\w*\sADC\s?\w*', name)[0]
            if not self.adc_count_found:
                self.adc_count_found = True
                return [('ADC', {'{}-bit'.format(adc_type): {'count': int(value)}})]
            else:
                return [('ADC', {'{}-bit'.format(adc_type): {'channels': int(value)}})]

        if 'DAC' in name and 'channels' in name:
            dac_type = re.findall('(\d+)-bit\s?\w*\sDAC\s?\w*', name)[0]
            if value.lower() == 'yes' and not self.dac_count_found:
                count = 1
                self.dac_count_found = True
                return [('DAC', {'{}-bit'.format(dac_type): {'count': int(count)}})]

            elif self.dac_count_found and is_numeric(value):
                return [('DAC', {'{}-bit'.format(dac_type): {'channels': int(value)}})]
            else:
                count, channels = value.split('\n')
                if count.lower() == 'yes':
                    count = 1
                else:
                    if is_numeric(count):
                        count = int(count)
                    else:
                        count = 0
            return [('DAC', {'{}-bit'.format(dac_type): {'count': int(count), 'channels': int(channels)}})]
        if 'Operating voltage' in name:
            if re.match('.*\s([\d.]+)\s.*\s([\d.]+)\s', value):
                lo, hi = re.findall('.*\s([\d.]+)\s.*\s([\d.]+)\s', value)[0]
                return [('Operating voltage', {'min': float(lo), 'max': float(hi)})]
            if 'v' in value.lower():
                value = remove_units(value, 'v')
            if 'v' in value.lower():
                value = remove_units(value, 'v')
            values = value.split('to')
            values = list(map(float, values))
            return [('Operating voltage', {'min': values[0], 'max': values[1]})]

        if 'SPI' in name:
            if 'Quad-SPI' in name:
                if value == '-' or value == '-':
                    spis = 0
                else:
                    if is_numeric(value):
                        spis = int(value)
                    else:
                        spis = 0
                return [('SPI', spis), ('Quad SPI', 1)]
            if '(' not in name:
                value = remove_parentheses(value)
            else:
                value = value.replace('(', '', 1).replace(')', '', 1)
            if 'I2S' in name and '/' in name:
                spis, i2ss = list(map(int, value.split('/')))
                return [('SPI', spis), ('I2S', i2ss)]
            if value.lower() == 'yes':
                value = 1
            else:
                if is_numeric(value):
                    value = int(value)
                else:
                    value = 0
            return [('SPI', int(value))]

        if 'Operating temperature' in name:
            # -40 to 85 °C / -40 to 125 °C
            if 'Ambient temperatures' in value:
                lo, hi = re.findall(r'([+-–]?\s?\d+)\sto\s([-+–]?\s?\d+)\s', value, re.IGNORECASE)[0]
                lo = lo.replace('–', '-').replace(' ', '')
                hi = hi.replace('–', '-').replace(' ', '')
                return [('Operating temperature', {'min': int(lo), 'max': int(hi)})]
            else:
                return [(None, None)]
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
                    self.adc_count_found = False
                    self.dac_count_found = False
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
                            current_stm_name = current_stm_name.replace(' ', '').replace(' ', '')
                            if self.mc_family.upper() not in current_stm_name.upper():
                                break
                            if not mcu_counter.get(current_stm_name, False):
                                mcu_counter[current_stm_name] = 1
                            if not controller_features.get(name, False):
                                controller_features[name] = {}
                            continue
                        feature_name = controller_features_names[feature_offset + n - 1]
                        feature_value = feature.text
                        try:
                            for n, v in self.handle_feature(feature_name, feature_value):
                                if n and v:
                                    _, v = convert_type(n, v)
                                    if controller_features[name].get(n, False):
                                        v = self.merge_features(controller_features[name].get(n), v)
                                        controller_features[name][n] = v
                                    else:
                                        controller_features[name][n] = v
                        except Exception as ex:
                            sys.stderr.write("FEATURE ERROR {}".format(ex))
                            traceback.print_exc()
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
    datasheet = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\stm32F\STM32F038F6.pdf")
    with open('./../config.json') as fp:
        config = json.load(fp)
    feature_extractor = STM32FFeatureListExtractor('STM32F038F6', datasheet, config)
    # feature_extractor.process()
    # feature_extractor.unify_names()
    pins = feature_extractor.extract_pinout()
    with open('./../pins.json', 'w') as fp:
        json.dump(pins, fp, indent=2)

    # pprint(feature_extractor.features)
