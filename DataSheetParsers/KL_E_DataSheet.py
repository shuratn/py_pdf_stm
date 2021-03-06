import os
import sys

from PyPDF3.pdf import PageObject

from DataSheetParsers.DataSheet import DataSheet, DataSheetTableNode
import re
from tqdm import tqdm

from DataSheetParsers.MK_E_DataSheet import MK_DataSheet


class KL_DataSheet(MK_DataSheet):
    FAMILY_NAME = re.compile(r'KL(\d+)', re.IGNORECASE | re.MULTILINE)


if __name__ == '__main__':
    # if len(sys.argv) < 1:
    #     print('Usage: {} DATASHEET.pdj DATASHEET2.pdf'.format(os.path.basename(sys.argv[0])))
    #     exit(0)
    a = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\KL\KL16P64M48SF4.pdf")
    pass