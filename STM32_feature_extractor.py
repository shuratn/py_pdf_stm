import os
import sys
from typing import List

from DumpPDFText import DataSheet
from PDFInterpreter import PDFInterpreter


class STM32FeaturesList:

    def __init__(self, stms: List[str]):
        """
        Class for comparing multiple STM32 controllers

        :type stms: list of stm controllers that you want to compare
        """
        self.stms = stms
        self.stm_datasheets = {}
        self.stm_features_tables = {}

    def gather_datasheets(self):
        for stm in self.stms:
            datasheet = DataSheet(stm)
            self.stm_datasheets[stm] = datasheet

    def extract_table(self, datasheet, page):
        print('Extracting table from {} page'.format(page+1))
        pdf_int = PDFInterpreter(pdf_file=datasheet.pdf_file, page=page)
        pdf_int.flip_page = True
        pdf_int.process()
        try:
            return pdf_int.table
        finally:
            del pdf_int

    def extract_tables(self):
        for stm in self.stms:
            print('Extracting tables for', stm)
            datasheet = self.stm_datasheets[stm]

            table_pt1 = self.extract_table(datasheet, 12)
            table_pt2 = self.extract_table(datasheet, 13)
            table_pt3 = self.extract_table(datasheet, 14)
            self.stm_features_tables[stm] = [table_pt1,table_pt2,table_pt3]


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: {} DATASHEET.pdj'.format(os.path.basename(sys.argv[0])))
        exit(0)
    controllers = sys.argv[1:]
    datasheet = STM32FeaturesList(controllers)
    datasheet.gather_datasheets()
    datasheet.extract_tables()
