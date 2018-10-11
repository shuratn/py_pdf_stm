import json
import re
import sys
import traceback
from pprint import pprint
from typing import Any, Dict

from PyPDF3.pdf import PageObject

from DataSheetParsers.DataSheet import DataSheet
from FeatureExtractors.MK_E_feature_extractor import MKFeatureListExtractor
from FeatureExtractors.feature_extractor import FeatureListExtractor
from DataSheetParsers.MK_E_DataSheet import MK_DataSheet
from TableExtractor import TableExtractor
from FeatureExtractors.feature_extractor import convert_type
from Utils import is_str, text2int, clean_line, fucking_split


class KVFeatureListExtractor(MKFeatureListExtractor):
    mcu_fields = re.compile(
        '(?P<q_status>[MP])(?P<s_fam>K)(?P<m_fam>V\d{2})(?P<key_attr>Z)(?P<flash>[\dM]{2,3})(?P<temp_range>\w)(?P<package>[a-zA-Z]+)(?P<cpu_frq>\d{1,3})(?P<pack_type>[R]?)',
        re.IGNORECASE)

    def __init__(self, controller: str, datasheet: DataSheet, config) -> None:
        super().__init__(controller, datasheet, config)

    def post_init(self):
        self.config_name = 'KE'
        self.mc_family = 'KE'

    def parse_code_name(self):  # UNIQUE FUNCTION FOR EVERY MCU FAMILY
        for mcu, features in self.features.items():
            mcus_fields = self.mcu_fields.match(mcu)
            qa_status, m_fam, s_fam_, key_attr, flash, temp, package, cpu_frq, pack_type = mcus_fields.groups()
            pin_count, package = self.packages[package]
            features[package] = 1
            features['pin count'] = pin_count
            if 'M' in flash:
                flash = flash.split('M')[0]
                flash = int(flash) * 1024
            else:
                flash = int(flash)
            features['flash'] = flash
            features['CPU Frequency'] = self.freqs[cpu_frq][0]
            features['operating temperature'] = {'lo': self.temperatures[temp][0], 'hi': self.temperatures[temp][1]}

    # def extract_fields(self):
    #     fields = self.datasheet.table_of_content.get_node_by_name('Fields')
    #     tables = []
    #     if fields:
    #         t1 = self.extract_table(self.datasheet, page=self.datasheet.get_page_num(fields.page))
    #         if t1:
    #             tables.extend(t1)
    #         t2 = self.extract_table(self.datasheet, page=self.datasheet.get_page_num(fields.page) + 1)
    #         if t2:
    #             tables.extend(t2)

    def extract_features(self):
        controller_features = {}
        pages = [self.datasheet.pdf_file.getPage(0), self.datasheet.pdf_file.getPage(1)]
        mcus = []
        ordering_info = self.datasheet.table_of_content.get_node_by_name('Ordering information')
        if ordering_info:
            or_page = self.datasheet.get_page_num(ordering_info.page)
            ordering_tables = self.extract_table(self.datasheet, or_page)
        else:
            ordering_tables = self.extract_table(self.datasheet, 1)
        for table in ordering_tables:
            if 'Ordering information'.lower() in table.get_cell(0, 0).text.lower():
                mcus = list(map(lambda cell: cell.clean_text, table.get_col(0)[3:]))
            elif 'Product' in table.get_cell(0, 0).text:
                mcus = list(map(lambda cell: cell.clean_text, table.get_col(0)[2:]))

        for page in pages:
            text = page.extractText()
            for block in text.split("€"):
                block = block.replace('\n', ' ')
                lines = fucking_split(block,'†‡°•')
                for line in lines:
                    self.extract_feature(line)
                #     print(line, '\n')
                # print('=' * 20)
                continue
                # print(block)
                # print('=' * 20)

        for mcu in mcus:
            if mcu:
                if not controller_features.get(mcu, False):
                    controller_features[mcu] = {}
                for common, value in self.common_features.items():
                    controller_features[mcu][common] = value

        return controller_features


if __name__ == '__main__':
    datasheet = MK_DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\KV\KV11P64M75.pdf")
    with open('./../config.json') as fp:
        config = json.load(fp)
    feature_extractor = KVFeatureListExtractor('KV11P64M75', datasheet, config)
    feature_extractor.process()
    feature_extractor.unify_names()
    pprint(feature_extractor.features)
