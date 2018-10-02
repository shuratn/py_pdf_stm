import re
import traceback

from KL_feature_extractor import KLFeatureListExtractor
from PDFInterpreter import PDFInterpreter
from feature_extractor import FeatureListExtractor


class MKFeatureListExtractor(KLFeatureListExtractor):
    table_cache = {}

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER

        print('Extracting tables for', self.controller)
        datasheet = self.datasheet
        family = re.findall(r'MK(\d+)\w+', self.controller)[0]  # MK11DN512AVMC5
        # print(family, sub_family)
        self.mc_name = None
        self.mc_family = 'MK{}'.format(family)
        for n, table in enumerate(self.datasheet.tables.values()):
            if table['name'].upper() == 'K{}'.format(family):
                self.mc_name = 'K{}-{}'.format(family, n)
                if self.mc_name in self.table_cache:
                    self.features_tables.extend(self.table_cache[self.mc_name])
                    return
                page_num = datasheet.get_page_num(table['data'])
                table = self.extract_table(datasheet, page_num)
                if table:
                    self.features_tables.extend(table)
                table = self.extract_table(datasheet, page_num-1)
                if table:
                    self.features_tables.extend(table)

    def extract_table(self, datasheet, page):
        print('Extracting table from {} page'.format(page))
        pdf_int = PDFInterpreter(str(datasheet.path))
        table = pdf_int.parse_page(page)
        self.update_cache(self.mc_name, table)
        return table

    def extract_features(self):
        self.name_corrector.update({
            'Total (KB)Flash Memory': 'Flash',
            'EEP(KB)ROM/FlexRAM': 'EEPROM/FlexRAM(KB)',
            'HiUgAh BRT auw/IdrSate O7816': 'High Baudrate UART w/ISO7816',
            'HiUgAh RTBaudrate': 'High Baudrate UART',
            'MPotWor MControl': 'Motor Control PWM',
            'QPuaWd MDecoder': 'Quad Decoder PWM',
            'TotDPal 16-bit ADC': 'Total 16-bit ADC DP',
            'RanGendoerm Nator umber': 'Random Number Generator',
            'SyAcmmetriceleratc Cror ypto': 'Symmetric Crypto Accelerator',
            'T(aDrmper yIce)Detect': 'Accelerator Tamper Detect (DryIce)',
            'NuTamber of Emper Pinsxternal': 'Number of External Tamper Pins',
            'Evalu(SeeatiPaon ge Bo17)ard': 'Evaluation Board (See Page 17)',
        })
        controller_features_names = []
        controller_features = {}
        feature_offset = 0
        for table in self.features_tables:
            try:
                if not table.global_map:
                    continue
                header = table.get_row(0)[2:]
                for feature_cell in header:  # fixing cell text
                    feature_cell.text = ''.join(feature_cell.text.split('\n')[::-1])
                # print(header)
                for row_id in range(1, len(table.get_col(1))):
                    row = table.get_row(row_id)[1:]
                    controller_name = row.pop(0).text
                    if 'Common Features' in controller_name or self.mc_family not in controller_name:
                        continue
                    if controller_name not in controller_features:
                        controller_features[controller_name] = {}
                    for feature, value in zip(header, row):
                        new_names_values = self.handle_feature(feature.text, value.text)
                        for feature, value in new_names_values:
                            if feature and value:
                                controller_features[controller_name][feature] = value
                    # print(row)


            except Exception as ex:
                print(ex)
                continue

        self.features = controller_features
        return controller_features

    def handle_feature(self, name, value):
        name = name.strip()
        name = self.name_corrector.get(name, name)
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
        if 'SPI + Chip Selects' in name:
            values = value.split('/')
            return [('SPI', values[0]), ('Chip Select', values[1])]
        if 'Evaluation Board' in name:
            return [(None, None)]

        if value == '-':
            value = 'No'
        return [(name, value)]

    @classmethod
    def update_cache(cls, table_name, table):
        if table_name in cls.table_cache:
            cls.table_cache[table_name].extend(table)
        else:
            cls.table_cache[table_name] = table
