from PyPDF3.pdf import PageObject
from tqdm import tqdm

from DataSheet import DataSheet, DataSheetTableNode
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
            # if 'Table' in page_text:
            #     # print(page_text)
            #
            #     table_names = self.FAMILY_NAME.findall(page_text)
            #     for table_name in table_names:
            #         table_node = DataSheetTableNode(table_name, [0], len(self.tables), page)
            #         self.table_root.append(table_node)
            #         self.tables[len(self.tables)] = {'name': table_name, 'data': page}
                    # print(table_name)

                # print(page_text)
                # input('kek')
        # print(self.tables)
