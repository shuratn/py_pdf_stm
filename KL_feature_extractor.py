import re
import traceback

from PDFInterpreter import PDFInterpreter
from feature_extractor import FeatureListExtractor


class KLFeatureListExtractor(FeatureListExtractor):
    table_cache = {}

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER
        print('Extracting tables for', self.controller)
        datasheet = self.datasheet
        family, sub_family = re.findall(r'KL(\d)(\d)\w+', self.controller)[0]
        # print(family, sub_family)
        self.mc_name = None
        self.mc_family = 'K{}'.format(family)
        for n, table in enumerate(self.datasheet.tables.values()):
            if table['name'].upper() == 'KL{}X'.format(family):
                self.mc_name = 'KL{}X-{}'.format(family, n)
                if self.mc_name in self.table_cache:
                    self.features_tables.extend(self.table_cache[self.mc_name])
                    return
                page_num = datasheet.get_page_num(table['data'])
                table = self.extract_table(datasheet, page_num)
                if table:
                    self.features_tables.extend(table)

    def extract_table(self, datasheet, page):
        print('Extracting table from {} page'.format(page + 1))
        pdf_int = PDFInterpreter(str(datasheet.path))
        table = pdf_int.parse_page(page)
        self.update_cache(self.mc_name, table)
        return table

    def extract_features(self):
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
                            controller_features[controller_name][feature] = value
                    # print(row)


            except Exception as ex:
                print(ex)
                continue

        self.features = controller_features
        return controller_features

    name_corrector = {
        'C(PMU FrHz)equency': 'CPU Frequency',
        'SSPI eleQTct Y (of #EChip ach SPI)': 'SPI QTY',
        'GPenWeral-PurM (6ch/2pcosh)e': 'SPI QTY',
        '(WSatcW/hHdoW)g': 'Watchdog(SW/HW)',
        '(N1o. 6 of Bit/A1D2 C MBit)odules': 'No. of ADC Modules (16 Bit/12 Bit)',
        'ADDC P) Channels (SE/': 'ADC Channels (SE/DP)',
        'IAnnaloputsg Comparator': 'Analog Comparator',
        'GPIHigO h-WitDrivh Interre Pinsupt/': 'GPIO With Interrupt/High-Drive Pins',
        'TTSI (oucCah) pCacitihanvne els': 'TSI (CapacitiveTouch) Channels',
        'Ev(Aaluatioppendin x BPoaard ge 17)': 'Evaluation Board(Appendix Page 17)',
    }

    def handle_feature(self, name, value):
        name = name.strip()
        name = self.name_corrector.get(name, name)
        if 'ADC Modules' in name:
            adc_types = re.findall(r'.*\((.*)/(.*)\)', name)[0]
            name = 'ADC Modules'
            values = value.split('/')
            return [name, {t: v for t, v in zip(adc_types, values)}]
        if 'Watchdog' in name:
            adc_types = re.findall(r'.*\((.*)/(.*)\)', name)[0]
            name = 'Watchdog'
            values = value.split('/')
            return [name, {t: v for t, v in zip(adc_types, values)}]
        if 'GPIO With Interrupt/High-Drive Pins' in name:
            adc_types = re.findall(r'.* (.*)/(.*) .*', name)[0]
            name = 'GPIO special pins'
            values = value.split('/')
            return [name, {t: v for t, v in zip(adc_types, values)}]
        if 'Evaluation Board' in name:
            return [None, None]

        if value == '-':
            value = 'No'
        return [name, value]

    @classmethod
    def update_cache(cls, table_name, table):
        if table_name in cls.table_cache:
            cls.table_cache[table_name].extend(table)
        else:
            cls.table_cache[table_name] = table
