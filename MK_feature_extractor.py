import re
import sys
import traceback

from PyPDF3.pdf import PageObject

from MKL_feature_extractor import MKLFeatureListExtractor
from PDFInterpreter import PDFInterpreter
from feature_extractor import FeatureListExtractor


class MKFeatureListExtractor(MKLFeatureListExtractor):
    table_cache = {}

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER
        print('Extracting tables for', self.controller)
        datasheet = self.datasheet
        family = re.findall(r'MK(\d+)\w+', self.controller)[0]  # MK11DN512AVMC5
        # print(family, sub_family)
        self.mc_name = None
        self.shared_features = {}
        self.config_name = 'MK'
        self.mc_family = 'MK{}'.format(family)
        self.page_text = ''
        for n, table in enumerate(self.datasheet.tables.values()):
            if table['name'].upper() == 'K{}'.format(family):
                self.mc_name = 'K{}-{}'.format(family, n)
                if self.mc_name in self.table_cache:
                    self.features_tables.extend(self.table_cache[self.mc_name])
                    return
                page_num = datasheet.get_page_num(table['data'])
                page = datasheet.pdf_file.pages[page_num]  # type:PageObject
                self.page_text += page.extractText()
                table = self.extract_table(datasheet, page_num)
                if table:
                    self.features_tables.extend(table)
                table = self.extract_table(datasheet, page_num - 1)
                if table:
                    self.features_tables.extend(table)

    def extract_table(self, datasheet, page):
        # print('Extracting table from {} page'.format(page))
        pdf_int = PDFInterpreter(str(datasheet.path))
        table = pdf_int.parse_page(page)
        self.update_cache(self.mc_name, table)
        return table

    def extract_features(self):
        controller_features = {}
        for table in self.features_tables:
            try:
                if not table.global_map:
                    continue
                header = table.get_row(0)[2:]
                for feature_cell in header:  # fixing cell text
                    feature_cell.text = ''.join(feature_cell.text.split('\n')[::-1])
                for row_id in range(1, len(table.get_col(1))):
                    row = table.get_row(row_id)[1:]
                    controller_name = row.pop(0).text
                    if 'Common Features' in controller_name:
                        if self.mc_family not in controller_name:
                            continue
                        self.handle_shared(row)
                        continue
                    if controller_name not in controller_features:
                        controller_features[controller_name] = {}
                    for feature, value in zip(header, row):
                        new_names_values = self.handle_feature(feature.text, value.text)
                        for feature, value in new_names_values:
                            if feature and value:
                                controller_features[controller_name][feature] = value
                    if 'quad spi' in self.page_text.lower():
                        controller_features[controller_name]['Quad SPI'] = 'Yes'
                    else:
                        controller_features[controller_name]['Quad SPI'] = 'No'
                    # print(row)



            except Exception as ex:
                sys.stderr.write("ERROR {}".format(ex))
                traceback.print_exc()
        for _, features in controller_features.items():
            features.update(self.shared_features)
        self.features = controller_features
        return controller_features

    def handle_feature(self, name, value):
        if '\u2013' in name:
            name = name.replace('\u2013','-')
        if type(value)==str:
            if '\u2013' in value:
                value = value.replace('\u2013','-')
        if value == '-':
            value = 0
        name = name.strip()
        if name in self.config['corrections']:
            name = self.config['corrections'][name]
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
        # if 'SPI + Chip Selects' in name:
        #     values = list(map(int, value.split('/')))
        #     return [('SPI', values[0])]
        if 'Evaluation Board' in name:
            return [(None, None)]

        return super().handle_feature(name, value)

    @classmethod
    def update_cache(cls, table_name, table):
        if table_name in cls.table_cache:
            cls.table_cache[table_name].extend(table)
        else:
            cls.table_cache[table_name] = table
