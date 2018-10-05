import json
import re
import sys
import traceback
from pprint import pprint

from PyPDF3.pdf import PageObject

from DataSheet import DataSheet
from MKL_feature_extractor import MKLFeatureListExtractor
from MK_DataSheet import MK_DataSheet
from TableExtractor import TableExtractor
from feature_extractor import FeatureListExtractor, convert_type


class MKFeatureListExtractor(MKLFeatureListExtractor):

    def __init__(self, controller: str, datasheet: DataSheet, config):
        super().__init__(controller, datasheet, config)

    def post_init(self):
        self.shared_features = {}
        self.config_name = 'MK'
        self.mc_family = 'MK'
        self.page_text = []

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER
        print('Extracting tables for', self.controller)
        datasheet = self.datasheet

        for n, table in enumerate(self.datasheet.tables.values()):
            if self.mc_family in table['name'].upper():
                page_num = datasheet.get_page_num(table['data'])
                page = datasheet.pdf_file.pages[page_num]  # type:PageObject
                table = self.extract_table(datasheet, page_num)
                if table:
                    text = page.extractText()
                    for _ in range(len(table)):
                        self.page_text.append(text)
                    self.features_tables.extend(table)
                page = datasheet.pdf_file.pages[page_num - 1]  # type:PageObject
                table = self.extract_table(datasheet, page_num - 1)
                if table:
                    text = page.extractText()
                    for _ in range(len(table)):
                        self.page_text.append(text)
                    self.features_tables.extend(table)

    def extract_table(self, datasheet, page):
        pdf_int = TableExtractor(str(datasheet.path))
        table = pdf_int.parse_page(page)
        return table

    def extract_features(self):
        controller_features = {}
        for table, text in zip(self.features_tables, self.page_text):
            try:
                self.handle_shared(text)
                if not table.global_map:
                    continue
                skip_firts = False
                if table.get_row(0)[0].text == 'Footnotes':
                    skip_firts = True
                if skip_firts:
                    header = table.get_row(0)[2:]
                else:
                    header = table.get_row(0)[1:]
                for feature_cell in header:  # fixing cell text
                    feature_cell.text = self.fix_name(feature_cell.text)
                    # feature_cell.text = ''.join(feature_cell.text.split('\n')[::-1])

                for row_id in range(1, len(table.get_col(1))):
                    row = table.get_row(row_id)
                    if skip_firts:
                        row.pop(0)
                    controller_name = row.pop(0).text
                    if self.mc_family not in controller_name:
                        continue
                    if controller_name not in controller_features:
                        controller_features[controller_name] = {}
                    for feature, value in zip(header, row):
                        try:
                            new_names_values = self.handle_feature(feature.text, value.text)
                            for new_feature, new_value in new_names_values:
                                if new_feature and new_value:
                                    feature, value = convert_type(new_feature, new_value)
                                    if controller_features[controller_name].get(feature, False):
                                        value = self.merge_features(controller_features[controller_name].get(feature),
                                                                    value)
                                        controller_features[controller_name][feature] = value
                                    else:
                                        controller_features[controller_name][feature] = value
                        except Exception as ex:
                            controller_features[controller_name][feature] = value
                            sys.stderr.write("ERROR {}".format(ex))
                            traceback.print_exc()

                    if 'quad spi' in text.lower():
                        controller_features[controller_name]['Quad SPI'] = 'Yes'
                    else:
                        controller_features[controller_name]['Quad SPI'] = 'No'

            except Exception as ex:
                sys.stderr.write("ERROR {}".format(ex))
                traceback.print_exc()
        for _, features in controller_features.items():
            features.update(self.shared_features)
        self.features = controller_features
        return controller_features

    def handle_feature(self, name, value):
        if '\u2013' in name:
            name = name.replace('\u2013', '-')
        if type(value) == str:
            if '\u2013' in value:
                value = value.replace('\u2013', '-')
        if value == '-':
            value = 0
        name = name.strip()
        name = self.fix_name(name)
        if 'ADC Modules' in name:
            adc_types = re.findall(r'.*\((.*)/(.*)\)', name)[0]
            name = 'ADC Modules'
            values = value.split('/')
            return [(name, {t: v for t, v in zip(adc_types, values)})]

        if 'Watchdog' in name:
            adc_types = re.findall(r'.*\((.*)/(.*)\)', name)[0]
            name = 'Watchdog'
            values = value.split('/')
            return [(name, {t: v for t, v in zip(adc_types, values)})]
        if 'GPIO With Interrupt/High-Drive Pins' in name:
            adc_types = re.findall(r'.* (.*)/(.*) .*', name)[0]
            name = 'GPIO special pins'
            values = value.split('/')
            return [(name, {t: v for t, v in zip(adc_types, values)})]
        if 'Evaluation Board' in name:
            return [(None, None)]

        return super().handle_feature(name, value)


if __name__ == '__main__':
    datasheet = MK_DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\MK\MK.pdf")
    with open('config.json') as fp:
        config = json.load(fp)
    feature_extractor = MKFeatureListExtractor('MK', datasheet, config)
    feature_extractor.process()
    feature_extractor.unify_names()
    pprint(feature_extractor.features)
