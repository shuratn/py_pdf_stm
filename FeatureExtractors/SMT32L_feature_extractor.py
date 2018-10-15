import json
import sys
import traceback
from pprint import pprint

import pdfplumber
from tqdm import tqdm

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
        name = name.upper()
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

        if 'PACKAGE' in name:
            values = re.split('(\D+\s?\d{1,3})', value)
            values = [fucking_replace(name, '\n ', '').strip() for name in values]
            return [('PACKAGE',[value for value in values if value])]

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

    def extract_pinout(self):
        pin_pages = []
        start = self.datasheet.table_of_content.get_node_by_name('Pinouts and pin description')
        start_page = self.datasheet.get_page_num(start._page)
        found = False
        dropped = False
        for page in tqdm(self.datasheet.plumber.pages[start_page:], desc='Scaning pages',
                         unit='pages'):  # type:pdfplumber.pdf.Page
            page_text = page.extract_text(x_tolerance=2, y_tolerance=5)
            if 'pin definitions' in page_text.lower():
                found = True
                pin_pages.append(page.page_number - 1)
                continue
            if found and not dropped:
                dropped = True
            if found and dropped:
                break
        tables = []
        for page in pin_pages:
            table = self.extract_table(self.datasheet, page)
            for t in table:
                if 'pin number' in t.get_cell(0,0).clean_text.lower():
                    tables.append(t)

        root = tables.pop(0)
        for cell in root.get_row(1):
            cell.text = self.fix_name(cell.text)
        for table in tables:
            for row in list(table.global_map.values())[2:]:
                root.global_map[len(root.global_map)] = row
        # for row in root.global_map.values():
        #     print(''.join([cell.text.replace(" \n", '').replace("\n", "").center(15, ' ') for cell in row.values()]))
        pin_number_span = 0
        first_pin_num_cell = root.get_cell(0, 0)
        for cell in root.get_row(0):
            if cell == first_pin_num_cell:
                pin_number_span += 1
        pin_name_col = pin_number_span
        packages = [cell.text for cell in root.get_row(1)[:pin_number_span]]
        for n, package in enumerate(packages):
            self.pin_data[package] = {'pins': {}}
            for row_id in range(len(root.global_map) - 2):
                pin_id = root.get_cell(n, row_id + 2).clean_text
                if pin_id != '-':
                    pin_name = remove_parentheses(root.get_cell(pin_name_col, row_id + 2).clean_text.replace(' \n', ''))
                    pin_type = root.get_cell(pin_name_col + 1, row_id + 2).clean_text.replace(' \n', '')
                    pin_funks = root.get_cell(pin_name_col + 4, row_id + 2) \
                        .clean_text \
                        .replace(' \n', '') \
                        .replace(' ', '') \
                        .split(',')
                    pin_add_funks = root.get_cell(pin_name_col + 5, row_id + 2) \
                        .clean_text \
                        .replace(' \n', '') \
                        .replace(' ', '') \
                        .split(',')
                    pin_funks += pin_add_funks
                    pin_funks = [remove_all_fuckery(funk) for funk in pin_funks if funk != '-']  # removing all shit
                    pin_funks = remove_doubles([funk for funk in pin_funks if funk])  # cleaning after removing all shit
                    if pin_name.startswith('P'):
                        pin_funks.append('GPIO')
                    self.pin_data[package]['pins'][pin_id] = {'name': pin_name, 'functions': pin_funks,
                                                              'type': pin_type}
        # pprint(pin_data)
        # print(packages)
        # print(pin_number_span)
        return self.pin_data


if __name__ == '__main__':
    datasheet = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\stm32L\STM32L431CB.pdf")
    with open('./../config.json') as fp:
        config = json.load(fp)
    feature_extractor = STM32LFeatureListExtractor('STM32L431CB', datasheet, config)
    # feature_extractor.process()
    feature_extractor.extract_pinout()
    pprint(feature_extractor.features)
    with open('./../pins.json', 'w') as fp:
        json.dump(feature_extractor.pin_data, fp, indent=2)
