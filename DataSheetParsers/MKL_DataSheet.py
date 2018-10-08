from PyPDF3.pdf import PageObject
from tqdm import tqdm

from DataSheetParsers.DataSheet import DataSheet, DataSheetTableNode
import re


class MKL_DataSheet(DataSheet):
    FAMILY_NAME = re.compile(r'SUB-FAMILY KL(\d+[X\d]+):[\w+ ]*', re.IGNORECASE | re.MULTILINE)

    def collect_tables(self):
        for page in tqdm(self.pdf_file.pages, desc='Reading pages', unit='pages'):  # type:PageObject
            page_text = page.extractText()
            if 'SUB-FAMILY KL' in page_text:
                res = self.FAMILY_NAME.findall(page_text)[0]
                table_node = DataSheetTableNode(res, [0], len(self.tables), page)
                self.table_root.append(table_node)
                self.tables[len(self.tables)] = {'name': 'MKL'+res, 'data': page}
