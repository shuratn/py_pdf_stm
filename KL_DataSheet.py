from PyPDF3.pdf import PageObject

from DataSheet import DataSheet, DataSheetTableNode
import re


class KL_DataSheet(DataSheet):
    TABLE_NAME_RE = re.compile(r'(Table \d+.*[\w+ ]+)', re.IGNORECASE | re.MULTILINE)

    def collect_tables(self):
        for page in self.pdf_file.pages:  # type:PageObject
            page_text = page.extractText()
            if 'Ordering Information' in page_text:
                table_node = DataSheetTableNode('Ordering Information', [0], len(self.tables), page)
                self.table_root.append(table_node)
                self.tables[len(self.tables)] = {'name': 'Ordering Information', 'data': page}
            if 'Table' in page_text:
                # print(page_text)

                table_names = self.TABLE_NAME_RE.findall(page_text)
                for table_name in table_names:
                    table_node = DataSheetTableNode(table_name, [0], len(self.tables), page)
                    self.table_root.append(table_node)
                    self.tables[len(self.tables)] = {'name': table_name, 'data': page}
                    # print(table_name)

                # print(page_text)
                # input('kek')
        print(self.tables)
