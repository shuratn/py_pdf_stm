import os
import sys

from PyPDF3.pdf import PageObject

from DataSheetParsers.DataSheet import DataSheet, DataSheetTableNode
import re
from tqdm import tqdm

from DataSheetParsers.MK_E_DataSheet import MK_DataSheet


class KE_DataSheet(MK_DataSheet):
    FAMILY_NAME = re.compile(r'KV(\d+)', re.IGNORECASE | re.MULTILINE)

    def collect_tables(self):
        pass

if __name__ == '__main__':
    # if len(sys.argv) < 1:
    #     print('Usage: {} DATASHEET.pdj DATASHEET2.pdf'.format(os.path.basename(sys.argv[0])))
    #     exit(0)
    a = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\KV\KV10P48M75.pdf")
    pass