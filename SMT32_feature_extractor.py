import json
import re
from pprint import pprint

from DataSheet import DataSheet
from Utils import *
from feature_extractor import FeatureListExtractor, remove_units


class STM32FeatureListExtractor(FeatureListExtractor):

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER
        print('Extracting tables for', self.controller)
        datasheet = self.datasheet
        self.config_name = 'STM32'

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
        self.mc_family = self.controller[:9]  # STM32L451

    def handle_feature(self, name, value):
        value = remove_parentheses(value)
        if name in self.config['corrections']:
            name = self.config['corrections'][name]
        if 'USART' in name or 'LPUART' in name or 'LPUART' in name:
            values = sum(map(int,value.split('\n')))
            return [('UART', values)]
        if 'GPIOs' in name and 'Wakeup' in name:
            values = value.split('\n')
            if 'or' in values[0]:
                values[0] = values[0].split('or')[0]
            if '(' in values[0]:
                values[0] = values[0][:values[0].index('(')]
            return [('GPIOs', int(values[0])), ('Wakeup pins', int(values[1]))]
        if 'ADC' in name and 'Number' in name:
            adc_type = re.findall('(\d+)-bit\s?\w*\sADC\s?\w*',name)[0]
            values = value.split('\n')
            return [('ADC', {'{}-bit'.format(adc_type): {'count': int(values[0]), 'channels': int(values[1])}})]
        if 'Operating voltage' in name:
            value = remove_units(value, 'v')
            values = value.split('to')
            values = list(map(float, values))
            return [('Operating voltage', {'min': values[0], 'max': values[1]})]

        if 'Packages' in name:
            values = value.split('\n')
            return [(name,'Yes') for name in values]

        if 'Operating temperature' in name:
            # -40 to 85 °C / -40 to 125 °C
            value = value.split('\n')[1]
            lo,hi = re.findall(r'(-?\d+)\sto\s(-?\d+)\s', value,re.IGNORECASE)[0]
            return [('Operating temperature', {'min': int(lo), 'max': int(hi)})]

        return super().handle_feature(name, value)
if __name__ == '__main__':
    datasheet = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\stm32\STM32L451.pdf")
    with open('config.json') as fp:
        config = json.load(fp)
    feature_extractor = STM32FeatureListExtractor('stm32L476', datasheet, config)
    feature_extractor.process()
    pprint(feature_extractor.features)
