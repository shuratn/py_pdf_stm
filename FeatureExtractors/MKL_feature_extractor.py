import json
import sys
import traceback
from pprint import pprint

from PyPDF3.pdf import PageObject

from DataSheetParsers.DataSheet import DataSheet
from DataSheetParsers.MKL_DataSheet import MKL_DataSheet
from TableExtractor import TableExtractor
from FeatureExtractors.feature_extractor import FeatureListExtractor, convert_type
from Utils import *


class MKLFeatureListExtractor(FeatureListExtractor):

    def __init__(self, controller: str, datasheet: DataSheet, config):
        super().__init__(controller, datasheet, config)
        self.shared_features = {}
        self.family, self.sub_family = '0', '0'
        self.page_text = []
        self.shared_features = {}
        self.mc_family = ''
        self.post_init()

    def post_init(self):
        self.shared_features = {}
        self.shared_features = {}
        self.config_name = 'MKL'
        self.mc_family = 'MKL'

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER
        print('Extracting tables for', self.controller)
        datasheet = self.datasheet

        for n, table in enumerate(self.datasheet.tables.values()):
            if self.mc_family in table['name'].upper():
                page_num = datasheet.get_page_num(table['data'])
                page = datasheet.pdf_file.pages[page_num]  # type:PageObject
                text = page.extractText()
                table = self.extract_table(datasheet, page_num)
                if table:
                    text = page.extractText()
                    for _ in range(len(table)):
                        self.page_text.append(text)
                    self.features_tables.extend(table)
                    # return

    def extract_table(self, datasheet, page):
        # print('Extracting table from {} page'.format(page + 1))
        pdf_int = TableExtractor(str(datasheet.path))
        table = pdf_int.parse_page(page)
        return table

    def handle_shared(self, text, ):
        # print(text)
        res = re.findall(r'Temp\srange:\s(-?\d+).*\sto\s(-?\d+).*', text, re.IGNORECASE)
        if res:
            lo, hi = res[0]
            self.shared_features['Operating temperature'] = {'min': int(lo), 'max': int(hi)}
        return

        # for cell in row:
        #     for sub_row in cell.text.split('\n'):
        #         if 'Temp Range:' in sub_row:
        #             if 'Operating temperature' not in self.shared_features:
        #                 lo, hi = re.findall('(-?\d+)\s.*to\s(-?\d+)\s', sub_row, re.IGNORECASE)[0]
        #                 self.shared_features['Operating temperature'] = {'min': int(lo), 'max': int(hi)}

    def extract_features(self):
        controller_features = {}
        for table, text in zip(self.features_tables, self.page_text):

            try:
                self.handle_shared(text)
                if not table.global_map:
                    continue
                header = table.get_row(0)[2:]
                for feature_cell in header:  # fixing cell text
                    feature_cell.text = self.fix_name(feature_cell.text)
                    # feature_cell.text = ''.join(feature_cell.text.split('\n')[::-1])
                for row_id in range(1, len(table.get_col(1))):
                    row = table.get_row(row_id)[1:]
                    controller_name = row.pop(0).text
                    # if 'Common Features' in controller_name:
                    #     if self.mc_family not in controller_name:
                    #         continue
                    #     self.handle_shared(row)
                    #     continue
                    if self.mc_family not in controller_name:
                        continue
                    if controller_name not in controller_features:
                        controller_features[controller_name] = {}
                    for feature, value in zip(header, row):
                        new_names_values = self.handle_feature(feature.text, value.text)
                        for feature, value in new_names_values:
                            if feature == 'ADC_CHANNELS':  # Special case
                                for adc_type, adc_values in controller_features[controller_name]['ADC'].items():
                                    adc_values['channels'] = value
                                continue
                            if feature and value:
                                feature, value = convert_type(feature, value)
                                if controller_features[controller_name].get(feature, False):
                                    value = self.merge_features(controller_features[controller_name].get(feature),
                                                                value)
                                    controller_features[controller_name][feature] = value
                                else:
                                    controller_features[controller_name][feature] = value
                    if 'quad spi' in text.lower():
                        controller_features[controller_name]['Quad SPI'] = 'Yes'
                    else:
                        controller_features[controller_name]['Quad SPI'] = 'No'




            except Exception as ex:
                sys.stderr.write("ERROR {}\n".format(ex))
                traceback.print_exc()
        for _, features in controller_features.items():
            features.update(self.shared_features)
        self.features = controller_features
        return controller_features

    def handle_feature(self, name, value):
        name = name.strip()
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
            if '/' in name:
                adc_types = re.findall(r'.*\((\d+) bit/(\d+) bit\)', name, re.IGNORECASE)[0]
            else:
                adc_types = ['12']
            values = value.split('/')
            adcs = {}
            for adc_type, value in zip(adc_types, values):
                if int(value) > 0:
                    adcs['{}-bit'.format(adc_type)] = {'count': int(value), 'channels': 0}
            return [('ADC', adcs)]

        if 'Total' in name and '(Channels)' in name:
            adc_type = re.findall('Total\s(\d+)-bit\s?ADC\s?', name)[0]
            return [('ADC', {'{}-bit'.format(adc_type): {'channels': int(value)}})]

        if 'DAC' in name:
            adc_type = name.split(' ')[0]
            if is_str(value):
                if '/' in value:
                    value = int(value.split('/')[0])
            if is_numeric(value):
                value = int(value)
            if value:
                return [('DAC', {adc_type: {'count': value}})]

        if 'ADC Channels' in name:
            value = sum(map(int, value.split('/')))
            return [('ADC_CHANNELS', value)]
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

        if 'SPI QTY (#Chip Select of Each SPI)' in name:
            values = value.split('(')
            spi_count = int(values.pop(0))
            cs_string = values.pop(0).replace(')', '')
            cs_count = sum(map(int, cs_string.split('/')))
            return [('SPI QTY', spi_count), ('Chip Select', cs_count)]
        if 'UART w/ ISO7816' in name:
            value = int(value)
            return [('UART', value), ]
        if 'Low-Power UART' in name:
            value = int(value)
            return [('UART', value), ]

        if 'package' in name.lower():
            return [(value, 'Yes')]

        try:
            return super().handle_feature(name, value)
        except:
            return [(name,value)]


if __name__ == '__main__':
    datasheet = MKL_DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\MKL\MKL.pdf")
    with open('./../config.json') as fp:
        config = json.load(fp)
    feature_extractor = MKLFeatureListExtractor('MKL28Z512VLL7', datasheet, config)
    feature_extractor.process()
    pprint(feature_extractor.features)
