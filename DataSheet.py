import os
import sys
from pathlib import Path
from typing import Dict, List, Set

import PyPDF3
from tqdm import tqdm
import requests
from PyPDF3.pdf import PageObject


def join(to_join, separator=' '):
    return separator.join(map(str, to_join))


class DataSheetNode:

    def __init__(self, name: str, path: List[int]):
        """
        Constructor of DataSheetNode class.

        Args:
            name: Name of node.
            path: TOC path.

        """
        self.path = path
        self.name = name
        self.childs = []  # type: List[DataSheetNode]
        self.parent = None  # type: DataSheetNode

    def __repr__(self):
        return '<{} {}-"{}">'.format(self.__class__.__name__, join(self.path, '.'), self.name)

    def get_node_by_path(self, path, prev_node: 'DataSheetNode' = None) -> 'DataSheetNode':
        """Finds node by it's TOC path.

            Args:
                path: node TOC path.
                prev_node: previous node, used for recursive iteration.

            Returns:
                None or DataSheetNode.
        """
        ret_node: 'DataSheetNode' = None
        if not prev_node:
            prev_node = self.get_root_node()
        if prev_node.path == path:
            return prev_node
        else:
            for child in prev_node.childs:
                ret_node = self.get_node_by_path(path, child)
                if ret_node:
                    return ret_node
        return ret_node

    def get_node_by_name(self, name, prev_node: 'DataSheetNode' = None) -> 'DataSheetNode':
        """Finds node by it's TOC path.

            Args:
                name: node name.
                prev_node: previous node, used for recursive iteration.
            Returns:
                None or DataSheetNode.
        """
        ret_node: 'DataSheetNode' = None
        if not prev_node:
            prev_node = self.get_root_node()
        if prev_node.name == name:
            return prev_node
        else:
            for child in prev_node.childs:
                ret_node = self.get_node_by_name(name, child)
                if ret_node:
                    return ret_node
        return ret_node

    def get_node_by_type(self, node_type, prev_node: 'DataSheetNode' = None) -> 'DataSheetNode':
        """Finds node by type.

            Args:
                node_type: node type.
                prev_node: previous node, used for recursive iteration.
            Returns:
                None or DataSheetNode.
        """
        ret_node: 'DataSheetNode' = None
        if not prev_node:
            prev_node = self.get_root_node()
        if prev_node.__class__ == node_type:
            return prev_node
        else:
            for child in prev_node.childs:
                ret_node = self.get_node_by_type(node_type, child)
                if ret_node:
                    return ret_node
        return ret_node

    def get_root_node(self, prev_node: 'DataSheetNode' = None) -> 'DataSheetNode':
        """Finds root node.

            Args:
                prev_node: previous node, used for recursive iteration.
            Returns:
                None or DataSheetNode.
        """
        if not prev_node:
            prev_node = self
        if prev_node.parent:
            return self.get_root_node(prev_node.parent)
        else:
            return prev_node

    def flatout(self, prev_node: 'DataSheetNode' = None) -> List['DataSheetNode']:
        """Flats whole node tree to 1D array.

            Args:
                prev_node: previous node, used for recursive iteration.
            Returns:
                List[DataSheetNode]
        """
        if not prev_node:
            prev_node = self.get_root_node()
        out = []
        for child in prev_node.childs:
            out.append(child)
            if child.childs:
                out.extend(child.flatout(child))
        return out

    def to_set(self) -> Set[str]:
        """Returns set with all node names in current node tree.

            Returns:
                Set[DataSheetNode]
        """
        flat_nodes = self.flatout()  # type: List[DataSheetNode]
        return set([node.name for node in flat_nodes])

    def child_diff(self, other: 'DataSheetNode'):
        nodes = set(self.childs)
        nodes2 = set(other.childs)
        diff = nodes.symmetric_difference(nodes2)
        return diff

    def append(self, node: 'DataSheetNode'):
        self.childs.append(node)
        node.parent = self

    def new(self, name, path):
        node = DataSheetNode(name, path)
        self.append(node)
        return self

    def print_tree(self, depth=0, prev_indent="", last=False):
        """Prints current element and it's childs"""
        indent = ""
        if depth:
            indent = prev_indent + ("├" if not last else "└") + "─" * depth * 2
        # print(indent,self,sep="")
        print(indent, self, sep="")
        if depth:
            indent = prev_indent + "│" + "\t" * depth
        if last:
            indent = prev_indent + " " + "\t" * depth

        if self.childs:
            for elem in self.childs:
                elem.print_tree(1, indent, elem == self.childs[-1])


class DataSheetTableNode(DataSheetNode):

    def __init__(self, name: str, path: List[int], table_number, page):
        super().__init__(name, path)
        self.path.append(table_number)
        self.table_number = table_number
        self._page = page

    def get_table_name(self):
        return self.name

    def get_data(self):
        return self._page.getObject()['/Contents'].getData().decode('cp1251')

    @property
    def page(self):
        return self._page.page.getObject()

    @property
    def table_name(self):
        return self.get_table_name()


class DataSheet:

    def __init__(self, datasheet_path):
        self.path = Path(datasheet_path)
        self.pdf_file = PyPDF3.PdfFileReader(self.path.open('rb'))
        self.raw_outline = []
        self.tables, self.figures = {}, {}  # type: Dict
        self.table_of_content = DataSheetNode('ROOT', [0])
        self.table_root = DataSheetNode('TABLES', [-1])
        self.table_of_content.append(self.table_root)
        self.flatten_outline()
        self.sort_raw_outline()
        self.collect_tables()

    def collect_tables(self):
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
                if 'Table' in name:
                    table_id = int(name.split('.')[0].split(' ')[-1])
                    table = DataSheetTableNode(name, [0, table_id], table_id, entry)
                    self.table_root.append(table)
                    if top_level_node:
                        table.path = top_level_node.path + [table_id]
                        top_level_node.append(table)
                    self.tables[table_id] = {'name': name, 'data': entry}
                elif 'Figure' in name:
                    figure_id = int(name.split('.')[0].split(' ')[-1])
                    self.figures[figure_id] = entry
                else:
                    tmp = name.split(' ')  # type: List[str]

                    if '.' in tmp[0]:
                        order = list(map(int, tmp[0].split('.')))

                        node = DataSheetNode(join(tmp[1:]), order)
                        node.parent = self.table_of_content
                        parent = node.get_node_by_path(order[:-1])
                        parent.append(node)
                    else:
                        if tmp[0].isnumeric():
                            node = DataSheetNode(join(tmp[1:]), [int(tmp[0])])
                            self.table_of_content.append(node)
                            # pos = self.recursive_create_toc([int(tmp[0])])
                            # pos['name'] = ' '.join(tmp[1:])
                        else:
                            node = DataSheetNode(name, [1])
                            self.table_of_content.append(node)
                    top_level_node = node

            else:
                # TODO
                pass

    def get_page_num(self, page):
        # return self.pdf_file.getPageNumber(page)
        for n, pdf_page in enumerate(self.pdf_file.pages):
            if pdf_page.raw_get('/Contents') == page.raw_get('/Contents'):
                return n
        return -1

    def get_difference(self, other: 'DataSheet'):
        print('Comparing {} and {}'.format(self.name, other.name))
        flat1 = self.table_of_content.to_set()
        flat2 = self.table_of_content.to_set()
        diff1 = flat1.difference(flat2)
        diff2 = flat2.difference(flat1)
        diff_test = flat1.symmetric_difference(flat2)
        if not diff1 and not diff2 and not diff_test:
            print('No difference')
        else:
            print(diff1)
            print(diff2)
            print(diff_test)


if __name__ == '__main__':
    if len(sys.argv) < 1:
        print('Usage: {} DATASHEET.pdj DATASHEET2.pdf'.format(os.path.basename(sys.argv[0])))
        exit(0)
    a = DataSheet(r"D:\PYTHON\py_pdf_stm\datasheets\KL\KL17P64M48SF6\KL17P64M48SF6_ds.pdf")
    # b.table_of_content.print_tree()
    # a.table_of_content.print_tree()
    table = a.table_root.childs[1]
    # print(table)
    # print(a.get_page_num(table.page))
    # a.get_difference(b)
    # a.table_of_content.print_tree()
    # print(a.table_of_content.get_node_by_type(DataSheetTableNode))
    # print(a.table_of_content.to_set())
    # print('Total letter count:', sum([len(page) for page in a.text.values()]))
    # with open('test.json', 'w') as fp:
    #     json.dump(a.text, fp, indent=1)
