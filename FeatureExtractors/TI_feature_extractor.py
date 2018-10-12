import json
import re
from pprint import pprint
from typing import Any, Dict

from PyPDF3.pdf import PageObject

from DataSheetParsers.DataSheet import DataSheet
from DataSheetParsers.TI_DataSheet import TI_DataSheet
from FeatureExtractors.MK_E_feature_extractor import MKFeatureListExtractor
from DataSheetParsers.MK_E_DataSheet import MK_DataSheet
from FeatureExtractors.feature_extractor import FeatureListExtractor
from Utils import is_str, text2int, clean_line, fucking_split, fucking_replace


class TIFeatureListExtractor(MKFeatureListExtractor):
    flash_re = re.compile('(?P<flash>\d{2,})(?P<unit>\w{2,3})?\s.*ROM.*', re.IGNORECASE)
    ram_re = re.compile('(?P<ram>\d+)(?P<unit>\w+)\s.*SRAM\s.*', re.IGNORECASE)
    cmp_re = re.compile('(?P<count>(\d+)).*comparator.?\s', re.IGNORECASE)
    gpio_re = re.compile('\((?P<count>\d+).*GPIO.*\)', re.IGNORECASE)
    adc_bits_re = re.compile('(?P<bits>\d+)-bit.*ADC.*', re.IGNORECASE)
    freq_re = re.compile('clock.*(?P<freq>\d{2,3})\s?MHZ.*', re.IGNORECASE)
    tsi_re = re.compile('capacitive.*(sensing|Touch)',re.IGNORECASE)
    def __init__(self, controller: str, datasheet: DataSheet, config) -> None:
        self.mcus = []
        super().__init__(controller, datasheet, config)

    def post_init(self):
        self.config_name = 'TI'
        self.mc_family = 'TI'

    def process(self):
        # self.extract_fields()
        self.collect_mcus()
        self.features = self.merge_features(self.extract_features(), self.features)
        return self.features

    def collect_mcus(self):
        table = self.datasheet.table_of_content.get_node_by_name('Device Information')
        if table:
            table = self.extract_table(self.datasheet, self.datasheet.get_page_num(table._page))[0]
            for row_id, row in table.global_map.items():
                if row_id == 0:
                    if row[0].text != 'PARTNUMBER':
                        return
                    continue
                mcus = row[0].text.split('\n')
                pin_count = int(row[1].text.split('(')[-1][:-1])
                package = fucking_replace(row[1].text, '()', '')
                self.mcus.extend(mcus)
                for mcu in mcus:
                    self.features[mcu] = {'Pin Count': pin_count, 'Package': package}

    def extract_feature(self, line):
        line = clean_line(line)
        line = text2int(line.lower())
        line = line.replace('dual', '2')
        if self.voltage_re.findall(line):
            lo, hi = self.voltage_re.findall(line)[0]
            self.create_new_or_merge('operating voltage', {'lo': float(lo), 'hi': float(hi)}, True)
        elif self.dma_re.findall(line) and 'channel' in line:
            channels = self.dma_re.findall(line)[0]
            self.create_new_or_merge('DMA', {'channels': int(channels), 'count': 1}, True)
        elif self.temperature_re.findall(line):
            lo, hi = self.temperature_re.findall(line)[0]
            lo, hi = map(lambda s: s.replace(' ', ''), (lo, hi))
            self.create_new_or_merge('operating temperature', {'lo': float(lo), 'hi': float(hi)})
        elif self.ram_re.findall(line):
            ram, unit = self.ram_re.findall(line)[0]
            ram = int(ram)
            if unit.upper() == 'MB':
                ram *= 1024
            self.create_new_or_merge('SRAM', int(ram))
        elif self.flash_re.findall(line):
            flash, unit = self.flash_re.findall(line)[0]
            flash = int(flash)
            if unit.upper() == 'MB':
                flash *= 1024
            self.create_new_or_merge('flash', int(flash))
        elif 'comparator' in line:
            if self.cmp_re.findall(line):
                count = self.cmp_re.findall(line)[0]
                if any(count):
                    count = int(count[0])
                else:
                    count = 1
            else:
                count = 1

            self.create_new_or_merge('analog comparator', count)
        elif self.dac_re.findall(line):
            count = self.dac_re.findall(line)[0]
            if any(count):
                count = int(count[0])
            else:
                count = 1
            self.create_new_or_merge('DAC', count)
        elif self.freq_re.findall(line):
            count = self.freq_re.findall(line)[0]
            if any(count):
                self.create_new_or_merge('CPU Frequency', count)

        elif self.gpio_re.findall(line):
            count = self.gpio_re.findall(line)[0]
            if any(count):
                count = int(count)
                self.create_new_or_merge('Total GPIOS', count)
            else:
                pass

        elif self.timer_re.findall(line):
            count = self.timer_re.findall(line)[0]
            if any(count):
                count = int(count[0])
            else:
                count = 1
            self.create_new_or_merge('timer', count)
        elif self.adc_bits_re.findall(line):
            bits = self.adc_bits_re.findall(line)[0]
            count = self.adc_count_re.findall(line)
            if any(count):
                count = int(count[0])
            else:
                count = 1
            channels = self.adc_channels_re.findall(line)
            if any(channels):
                channels = int(channels[0])
            else:
                channels = 0
            if channels:
                self.create_new_or_merge('ADC', {
                    '{}-bit'.format(bits): {'count': count, 'channels': channels}})
            else:
                self.create_new_or_merge('ADC', {'{}-bit'.format(bits): {'count': count}})
        if 'SPI' in line.upper():
            if self.spi_re.findall(line):
                count = self.spi_re.findall(line)[0]
                self.create_new_or_merge('SPI', int(count))
            else:
                self.create_new_or_merge('SPI', 1)
        if 'UART' in line.upper():
            if self.uart_re.findall(line):
                count = self.uart_re.findall(line)[0]
                if any(count):
                    self.create_new_or_merge('uart', int(count))
                else:
                    self.create_new_or_merge('uart', 1)
            else:
                self.create_new_or_merge('uart', 1)
        if 'I2C' in line.upper():
            if self.i2c_re.findall(line):
                count = self.i2c_re.findall(line)[0]
                self.create_new_or_merge('I2C', int(count))
            else:
                self.create_new_or_merge('I2C', 1)
        if 'LCD' in line:
            self.create_new_or_merge('LCD', 1)
        if self.tsi_re.match(line):
            self.create_new_or_merge('TSI', 1)

    def extract_features(self):
        controller_features = {}
        pages = [self.datasheet.plumber.pages[0], self.datasheet.plumber.pages[1]]
        for page in pages:
            text = page.extract_text(y_tolerance=5, x_tolerance=2)
            for block in text.split("•"):
                block = block.replace('\n', ' ')
                lines = fucking_split(block, '†‡°•–')
                for line in lines:
                    if len(line) > 1000:
                        continue
                    self.extract_feature(line)
                continue
                # print(block)
                # print('=' * 20)
        for mcu in self.mcus:
            if not controller_features.get(mcu, False):
                controller_features[mcu] = {}
            for common, value in self.common_features.items():
                controller_features[mcu][common] = value

        return controller_features


if __name__ == '__main__':
    datasheet = TI_DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\MSP\msp432p4011t.pdf")
    with open('./../config.json') as fp:
        config = json.load(fp)
    feature_extractor = TIFeatureListExtractor('msp432p4011t', datasheet, config)
    feature_extractor.process()
    feature_extractor.unify_names()
    pprint(feature_extractor.features)
