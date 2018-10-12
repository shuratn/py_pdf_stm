import os
import sys
import traceback
import unicodedata
from pathlib import Path
from typing import Dict, List, Set

import PyPDF3
from tqdm import tqdm
import requests
from PyPDF3.pdf import PageObject
import pdfplumber
from DataSheetParsers.DataSheet import DataSheet, DataSheetNode, DataSheetTableNode, join


class TI_DataSheet(DataSheet):

    def collect_tables(self):
        # print('NO TABLES WERE DETECTED IN OUTLINE! FALLING BACK TO PAGE SCANNING!')
        start_page = 0
        end_page = 0
        for thing in self.raw_outline:
            if 'Description' in thing['/Title']:
                start_page = self.get_page_num(thing.page.getObject())
            if 'Functional' in thing['/Title']:
                end_page = self.get_page_num(thing.page.getObject())
                break
        for page_num in range(start_page, end_page):
            page = self.plumber.pages[page_num]
            text = page.extract_text(y_tolerance=3,x_tolerance=2)
            if 'Device Information' in text:
                page = self.pdf_file.pages[page_num]
                table = DataSheetTableNode('Device Information', [0, 9999], 9999,
                                           page)
                self.table_root.append(table)
                self.fallback_table = table
                break
        pass

    def flatten_outline(self, line=None):
        if line is None:
            line = self.pdf_file.getOutlines()
        for i in line:
            if isinstance(i, list):
                self.flatten_outline(i)
            else:
                self.raw_outline.append(i)

    def sort_raw_outline(self):
        top_level_node = None
        for entry in self.raw_outline:
            if entry['/Type'] == '/XYZ':
                name = entry['/Title']
                name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
                if 'Table' in name:
                    try:
                        table_id = int(name.split('.')[0].split(' ')[-1])
                        table = DataSheetTableNode(name, [0, table_id], table_id, entry)
                        self.table_root.append(table)
                        if top_level_node:
                            table.path = top_level_node.path + [table_id]
                            top_level_node.append(table)
                        self.tables[table_id] = {'name': name, 'data': entry}
                    except Exception as ex:
                        pass
                else:
                    tmp = name.split(' ')  # type: List[str]

                    if '.' in tmp[0]:
                        try:
                            order = list(map(int, tmp[0].split('.')))
                        except ValueError:
                            continue

                        node = DataSheetNode(join(tmp[1:]), order)
                        node._page = entry.page.getObject()
                        node._page_plumber = self.plumber.pages[self.get_page_num(entry.page.getObject())]
                        node.parent = self.table_of_content
                        parent = node.get_node_by_path(order[:-1])
                        parent.append(node)
                    else:
                        if tmp[0].isnumeric():
                            node = DataSheetNode(join(tmp[1:]), [int(tmp[0])])
                            node._page = entry.page.getObject()
                            node._page_plumber = self.plumber.pages[self.get_page_num(entry.page.getObject())]
                            self.table_of_content.append(node)
                            # pos = self.recursive_create_toc([int(tmp[0])])
                            # pos['name'] = ' '.join(tmp[1:])
                        else:
                            node = DataSheetNode(name, [1])
                            node._page = entry.page.getObject()
                            node._page_plumber = self.plumber.pages[self.get_page_num(entry.page.getObject())]
                            self.table_of_content.append(node)
                    top_level_node = node

            else:
                pass

    def get_page_num(self, page):
        # return self.pdf_file.getPageNumber(page)
        for n, pdf_page in enumerate(self.pdf_file.pages):
            if pdf_page.raw_get('/Contents') == page.raw_get('/Contents'):
                return n
        return -1


if __name__ == '__main__':
    if len(sys.argv) < 1:
        print('Usage: {} DATASHEET.pdj DATASHEET2.pdf'.format(os.path.basename(sys.argv[0])))
        exit(0)
    # a = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\stm32f\stm32f777vi.pdf")
    a = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\TI\cc1312r.pdf")
    # b.table_of_content.print_tree()
    # a.table_of_content.print_tree()
    table = a.table_root.childs[1] if a.table_root.childs else a.fallback_table
    print(table)
    # print(table)
    # print(a.get_page_num(table.page))
    # a.get_difference(b)
    # a.table_of_content.print_tree()
    # print(a.table_of_content.get_node_by_type(DataSheetTableNode))
    # print(a.table_of_content.to_set())
    # print('Total letter count:', sum([len(page) for page in a.text.values()]))
    # with open('test.json', 'w') as fp:
    #     json.dump(a.text, fp, indent=1)
