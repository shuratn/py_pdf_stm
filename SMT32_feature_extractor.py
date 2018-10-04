import re

from feature_extractor import FeatureListExtractor


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
        if name in self.config['corrections']:
            name = self.config['corrections'][name]
        if 'USART' in name and 'LPUART' in name:
            values = value.split('\n')
            return [('USART', values[0]), ('LPUART', values[1])]
        if 'GPIOs' in name and 'Wakeup' in name:
            values = value.split('\n')
            if 'or' in values[0]:
                values[0] = values[0].split('or')[0]
            if '(' in values[0]:
                values[0] = values[0][:values[0].index('(')]
            return [('GPIOs', values[0]), ('Wakeup pins', values[1])]
        if 'ADC' in name and 'Number' in name:
            adc_type = name.split('ADC')[0]
            values = value.split('\n')
            return [('ADC', {adc_type: {'count': values[0], 'channels': values[1]}})]
        if 'Operating voltage' in name:
            value = self.remove_units(value, 'v')
            values = value.split('to')
            values = list(map(float, values))
            return [('Operating voltage', {'min': values[0], 'max': values[1]})]

        if 'Packages' in name:
            return [('Package', value.split('\n'))]

        if 'Operating temperature' in name:
            # -40 to 85 °C / -40 to 125 °C
            value = value.split('\n')[1]
            lo,hi = re.findall(r'(-?\d+)\sto\s(-?\d+)\s', value,re.IGNORECASE)[0]
            return [('Operating temperature', {'min': int(lo), 'max': int(hi)})]

        return super().handle_feature(name, value)
