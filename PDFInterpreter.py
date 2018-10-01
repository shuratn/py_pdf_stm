import copy
import math
import random
from functools import partial
from typing import Tuple

import pdfplumber
from DataSheet import *

DEBUG = True
PRINT_PARSING = False




class Table:

    def __init__(self, cells:List[List[str]]):
        self.cells = cells
        self.global_map = {}


    def build_table(self):
        for y, row in self.table_skeleton.items():
            self.global_map[y] = {}
            for x, cell in enumerate(row):
                for t_cell in self.cells:
                    if t_cell.point_inside_polygon(cell.center):
                        self.global_map[y][x] = t_cell

        for text_point in self.texts:
            for cell in self.cells:
                _, p1 = text_point
                if cell.point_inside_polygon(p1):
                    cell.texts.append(text_point)

        for cell in self.cells:
            cell.draw(self.canvas)

    def get_col(self, col_id) -> List[Cell]:
        col = []
        for row in self.global_map.values():
            col.append(row[col_id])
        return col

    def get_row(self, row_id) -> List[Cell]:
        return list(self.global_map[row_id].values())

    def get_cell(self, x, y) -> Cell:
        return self.global_map[y][x]

    def get_cell_span(self, cell):
        temp = {}
        for row_id, row in self.global_map.items():

            for col_id, t_cell in row.items():
                if t_cell == cell:
                    if not temp.get(row_id, False):
                        temp[row_id] = {}
                    temp[row_id][col_id] = True
        row_span = len(temp)
        col_span = len(list(temp.values())[0])
        return row_span, col_span

    def print_table(self):
        rows = len(self.table_skeleton)
        cols = len(self.table_skeleton[0])
        for col in range(cols):
            for row in range(rows):
                self.global_map[row][col].print_cell()

    # def join_splitted_table(self, other: 'Table', strip_header=True,ignore_header_error = False):
    #     for row_id, row in other.global_map.items():
    #         if strip_header and row_id == 0:
    #             for cell1,cell2 in zip(self.global_map[0].values(),row.values()):
    #                 if cell1.text != cell2.text and not ignore_header_error:
    #                     raise Exception('''Tables header aren\'t identical\n'
    #                                     if you want to ignore this error set ignore_header_error = True''')
    #             continue
    #         self.global_map[len(self.global_map)] = row


class PDFInterpreter:

    def __init__(self, table_node: DataSheetTableNode = None, pdf_file=None, page: int = None):
        if table_node:
            self.table = table_node
            self.page = self.table.page
            self.content = self.table.get_data()
            self.name = self.table.name.split('.')[0]

        if page and pdf_file:
            self.page = pdf_file.pages[page]
            self.content = self.page['/Contents'].getData().decode('cp1251')
            self.name = 'page-{}'.format(page)

    def process(self):
        self.prepare()
        self.parse()
        self.render()
        if len(self.lines) > 200:
            print('Not a table')
            return
        # self.build_skeleton()
        # self.rebuild_table()
        # self.table.build_table()



# def pdfplumber_table_to_table():


if __name__ == '__main__':
    datasheet = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\KL\KL17P64M48SF6\KL17P64M48SF6_ds.pdf")
    # datasheet = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\stm32\stm32L431\stm32L431_ds.pdf")
    pdf_interpreter = PDFInterpreter(pdf_file=datasheet.pdf_file, page=1)
    pdf_interpreter.draw = True
    pdf_interpreter.debug = True
    # pdf_interpreter = PDFInterpreter(pdf.table_root.childs[table])
    pdf_interpreter.flip_page = True
    # print(pdf_interpreter.content)
    pdf_interpreter.process()
    pdf_interpreter.save()
    # pdf_interpreter.table.print_table()
