import copy
import math
import random
from functools import partial
from itertools import cycle, zip_longest
from pprint import pprint
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont, ImageColor
from pyparsing import *

from DumpPDFText import *

DEBUG = False


def debug_print(*a, name="OPCODE"):
    string = a[0]
    offset = a[1] or 1
    from_ = 0
    if type(a[2]) == int:
        from_ = a[2]
        a = a[3:]
    print('Parsing', name, ':')
    # print('Searching for',a[0])
    print(from_, offset)
    print('"{}"'.format(string))
    print(('-' * (offset)) + '^')
    print(a[2:])
    print()


def parse_number(string):
    string = string[0]
    if '.' in string:
        return float(string)
    else:
        return int(string)


def parse_text_args(text):
    if len(text) == 2:
        return text[1], text[0]
    return text[0], 0.0


def parse_command(text):
    opcode = text[-1]
    args = text[:-1]
    # print(opcode,args)
    return opcode, args


OPCODE = Word(alphas + '*')
DOT = Literal('.')
LBR = Literal("(").suppress()
RBR = Literal(")").suppress()
LSBR = Literal("[").suppress()
RSBR = Literal("]").suppress()
LTBR = Literal("<").suppress()
RTBR = Literal(">").suppress()
PLUSORMINUS = Literal('+') | Literal('-')
OPLUSORMINUS = Optional(PLUSORMINUS)

NUMBERS = Word(nums)
NUMBER = Combine(OPLUSORMINUS + NUMBERS + DOT + NUMBERS) | Combine(OPLUSORMINUS + DOT + NUMBERS) | Combine(
    OPLUSORMINUS + NUMBERS)
NUMBER.setParseAction(parse_number)
ONLY_TEXT = Word(alphanums + ' .\\/&!@#$%^-–=+*µ_,?;:®Ђ™°’±~<>|"\'').leaveWhitespace()
TEXT = (LBR + ONLY_TEXT + RBR) | (LTBR + ONLY_TEXT + RTBR)

TEXT_ARGS = Optional(NUMBER) + TEXT
TEXT_ARGS.setParseAction(parse_text_args)

# TEXT_ARGS = Regex(r'((-?(\d+)?\.?(\d*\([\w\d\s]+\))))')
SPACE = Literal(' ').suppress()
COMMAND = ((LSBR + OneOrMore(TEXT_ARGS) + RSBR) + OPCODE) | \
          (OneOrMore(NUMBER) + OPCODE) | \
          TEXT + OPCODE | \
          ONLY_TEXT + ZeroOrMore(NUMBER) + OPCODE | \
          OPCODE
COMMAND.setParseAction(parse_command)
if DEBUG:
    OPCODE.debug = DEBUG
    OPCODE.debugActions = (debug_print, debug_print, debug_print)

    dd = partial(debug_print, name='NUMBER')
    NUMBER.debug = DEBUG
    NUMBER.debugActions = (dd, dd, dd)

    dd = partial(debug_print, name='TEXT')
    TEXT.debug = DEBUG
    TEXT.debugActions = (dd, dd, dd)

    dd = partial(debug_print, name='ONLY_TEXT')
    ONLY_TEXT.debug = DEBUG
    ONLY_TEXT.debugActions = (dd, dd, dd)

    dd = partial(debug_print, name='TEXT_ARGS')
    TEXT_ARGS.debug = DEBUG
    TEXT_ARGS.debugActions = (dd, dd, dd)

    COMMAND.debug = DEBUG
    dd = partial(debug_print, name='COMMAND')
    COMMAND.debugActions = (dd, dd, None)


# # a = '-29964.8'
# a = '/GS1 gs'
# # print(NUMBER.parseString(a))
# print(OneOrMore(COMMAND).parseString(a))
# exit(1)

def almost_equals(a, b, precision=3.0):
    return abs(a - b) < precision


class Point:
    r = 4
    hr = r / 2
    tail = 5

    def __init__(self, *xy):
        if len(xy) == 1:
            xy = xy[0]
        self.x, self.y = xy
        self.x = math.ceil(self.x)
        self.y = math.ceil(self.y)
        self.d = False
        self.u = False
        self.l = False
        self.r = False

    @property
    def symbol(self):
        table = {
            (False, False, False, False): '●',

            (True, False, False, False): '↑',
            (False, True, False, False): '↓',
            (True, True, False, False): '↕',

            (True, True, True, False): '⊢',
            (True, True, False, True): '⊣',

            (False, False, True, False): '→',
            (False, False, False, True): '←',
            (False, False, True, True): '↔',

            (True, False, True, True): '⊥',
            (False, True, True, True): '⊤',

            (True, True, True, True): '╋',

            (True, False, True, False): '┗',
            (True, False, False, True): '┛',

            (False, True, True, False): '┏',
            (False, True, False, True): '┛',

        }
        return table[(self.u, self.d, self.r, self.l)]

    def __repr__(self):
        return "Point<X:{} Y:{} {} >".format(self.x, self.y, self.symbol)

    @property
    def as_tuple(self):
        return (self.x, self.y)

    def draw(self, canvas: ImageDraw.ImageDraw, color='red'):
        canvas.ellipse((self.x - self.hr, self.y - self.hr, self.x + self.hr, self.y + self.hr), fill=color)
        if self.d:
            canvas.line(((self.x, self.y), (self.x, self.y + self.tail)), 'blue')
        if self.u:
            canvas.line(((self.x, self.y), (self.x, self.y - self.tail)), 'blue')
        if self.l:
            canvas.line(((self.x, self.y), (self.x - self.tail, self.y)), 'blue')
        if self.r:
            canvas.line(((self.x, self.y), (self.x + self.tail, self.y)), 'blue')

    def points_to_right(self, other_points: List['Point']):
        sorted_other_points = sorted(other_points, key=lambda other: other.x)
        filtered_other_points = filter(lambda o: almost_equals(o.y, self.y) and o != self and o.x > self.x,
                                       sorted_other_points)
        return list(filtered_other_points)

    def points_below(self, other_points: List['Point']):
        sorted_other_points = sorted(other_points, key=lambda other: other.y)
        filtered_other_points = filter(lambda o: almost_equals(o.x, self.x) and o != self and o.y > self.y,
                                       sorted_other_points)
        return list(filtered_other_points)

    def on_same_line(self, other: 'Point'):
        if self == other:
            return False
        if almost_equals(self.x, other.x) or almost_equals(self.y, other.y):
            return True
        return False

    def is_above(self, other: 'Point'):
        return self.y < other.y

    def is_to_right(self, other: 'Point'):
        return self.x > other.x

    def get_right(self, others: List['Point']):
        others = self.points_to_right(others)
        for point in others:
            if point.d:
                return point
        return None

    def get_bottom(self, others: List['Point'], left=False, right=False):
        others = self.points_below(others)
        for point in others:
            if point.u:
                if left:
                    if not point.r:
                        continue
                if right:
                    if not point.l:
                        continue
                return point
        return None

    def copy(self, other: 'Point'):
        self.d = other.d
        self.u = other.u
        self.l = other.l
        self.r = other.r

    def __eq__(self, other: 'Point'):

        return abs(self.x - other.x) < 4 and abs(self.y - other.y) < 4


class Line:

    def __init__(self, p1: 'Point', p2: 'Point'):
        self.p1 = p1
        self.p2 = p2
        self.vertical = almost_equals(self.x, self.cx)
        if self.vertical:
            if self.p1.is_above(self.p2):
                pass
            else:
                self.p1, self.p2 = self.p2, self.p1
        else:
            if self.p2.is_to_right(self.p1):
                pass
            else:
                self.p1, self.p2 = self.p2, self.p1

        if self.vertical:
            self.p1.d = True
            self.p2.u = True
        else:
            self.p1.r = True
            self.p2.l = True

    @property
    def x(self):
        return self.p1.x

    @property
    def y(self):
        return self.p1.y

    @property
    def cx(self):
        return self.p2.x

    @property
    def cy(self):
        return self.p2.y

    def __repr__(self):
        return 'Line<p1:{} p2:{} {}>'.format(self.p1, self.p2, 'vertical' if self.vertical else 'horizontal')

    def draw(self, canvas: ImageDraw.ImageDraw, color='blue'):
        x, y = self.x, self.y
        cx, cy = self.cx, self.cy

        canvas.line(((x, y), (cx, cy)), color, width=2)

    @property
    def as_tuple(self):
        return (self.x, self.y), (self.cx, self.cy)

    @staticmethod
    def _slope(P1, P2):
        # dy/dx
        # (y2 - y1) / (x2 - x1)
        return (P2[1] - P1[1]) / (P2[0] - P1[0])

    @staticmethod
    def _y_intercept(P1, slope):
        # y = mx + b
        # b = y - mx
        # b = P1[1] - slope * P1[0]
        return P1[1] - slope * P1[0]

    @staticmethod
    def _line_intersect(m1, b1, m2, b2):
        if m1 == m2:
            print("These lines are parallel!!!")
            return None
        # y = mx + b
        # Set both lines equal to find the intersection point in the x direction
        # m1 * x + b1 = m2 * x + b2
        # m1 * x - m2 * x = b2 - b1
        # x * (m1 - m2) = b2 - b1
        # x = (b2 - b1) / (m1 - m2)
        x = (b2 - b1) / (m1 - m2)
        # Now solve for y -- use either line, because they are equal here
        # y = mx + b
        y = m1 * x + b1
        return x, y

    def infite_intersect(self, other: 'Line'):
        line1 = self.as_tuple
        line2 = other.as_tuple
        x_diff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
        y_diff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])  # Typo was here

        def det(a, b):
            return a[0] * b[1] - a[1] * b[0]

        div = det(x_diff, y_diff)
        if div == 0:
            return None, None
        d = (det(*line1), det(*line2))
        x = det(d, x_diff) / div
        y = det(d, y_diff) / div
        return x, y

    def intersect(self, other: 'Line', print_fulness=False) -> bool:
        """ this returns the intersection of Line(pt1,pt2) and Line(ptA,ptB)
              returns a tuple: (xi, yi, valid, r, s), where
              (xi, yi) is the intersection
              r is the scalar multiple such that (xi,yi) = pt1 + r*(pt2-pt1)
              s is the scalar multiple such that (xi,yi) = pt1 + s*(ptB-ptA)
                  valid == 0 if there are 0 or inf. intersections (invalid)
                  valid == 1 if it has a unique intersection ON the segment    """
        pt1 = self.x, self.y
        pt2 = self.cx, self.cy
        ptA = other.x, other.y
        ptB = other.cx, other.cy
        if self.vertical:
            if self.y > self.cy:
                if self.y >= other.y >= self.cy:
                    pass
                else:
                    return False
        else:
            if other.y > other.cy:
                if other.y >= self.y >= other.cy:
                    pass
                else:
                    return False
        DET_TOLERANCE = 0.0001
        # the first line is pt1 + r*(pt2-pt1)
        # in component form:
        x1, y1 = pt1
        x2, y2 = pt2
        dx1 = x2 - x1
        dy1 = y2 - y1
        # the second line is ptA + s*(ptB-ptA)
        x, y = ptA
        xB, yB = ptB
        dx = xB - x
        dy = yB - y
        # we need to find the (typically unique) values of r and s
        # that will satisfy
        #
        # (x1, y1) + r(dx1, dy1) = (x, y) + s(dx, dy)
        #
        # which is the same as
        #
        #    [ dx1  -dx ][ r ] = [ x-x1 ]
        #    [ dy1  -dy ][ s ] = [ y-y1 ]
        #
        # whose solution is
        #
        #    [ r ] = _1_  [  -dy   dx ] [ x-x1 ]
        #    [ s ] = DET  [ -dy1  dx1 ] [ y-y1 ]
        #
        # where DET = (-dx1 * dy + dy1 * dx)
        #
        # if DET is too small, they're parallel
        #
        DET = (-dx1 * dy + dy1 * dx)

        if math.fabs(DET) < DET_TOLERANCE:
            print('Lines are parallel')
            return False
        # now, the determinant should be OK
        DETinv = 1.0 / DET
        # find the scalar amount along the "self" segment
        r = DETinv * (-dy * (x - x1) + dx * (y - y1))
        # find the scalar amount along the input line
        s = DETinv * (-dy1 * (x - x1) + dx1 * (y - y1))
        # return the average of the two descriptions
        if print_fulness:
            print('self segment', r)
            print('other segment', s)
        if r > 1 or s > 1:  # can't be higher than 1, 1 means they are NOT intersecting
            return False
        if r > -0.1 and s > -0.1:  # This can happen on edges, so we allow small inaccuracy
            return True
        return False

    def intersection(self, other: 'Line', print_fulness=False) -> (int, int):
        """ this returns the intersection of Line(pt1,pt2) and Line(ptA,ptB)
                      returns a tuple: (xi, yi, valid, r, s), where
                      (xi, yi) is the intersection
                      r is the scalar multiple such that (xi,yi) = pt1 + r*(pt2-pt1)
                      s is the scalar multiple such that (xi,yi) = pt1 + s*(ptB-ptA)
                          valid == 0 if there are 0 or inf. intersections (invalid)
                          valid == 1 if it has a unique intersection ON the segment    """
        pt1 = self.x, self.y
        pt2 = self.cx, self.cy
        ptA = other.x, other.y
        ptB = other.cx, other.cy

        DET_TOLERANCE = 1
        # the first line is pt1 + r*(pt2-pt1)
        # in component form:
        x1, y1 = pt1
        x2, y2 = pt2
        dx1 = x2 - x1
        dy1 = y2 - y1
        # the second line is ptA + s*(ptB-ptA)
        x, y = ptA
        xB, yB = ptB
        dx = xB - x
        dy = yB - y
        # we need to find the (typically unique) values of r and s
        # that will satisfy
        #
        # (x1, y1) + r(dx1, dy1) = (x, y) + s(dx, dy)
        #
        # which is the same as
        #
        #    [ dx1  -dx ][ r ] = [ x-x1 ]
        #    [ dy1  -dy ][ s ] = [ y-y1 ]
        #
        # whose solution is
        #
        #    [ r ] = _1_  [  -dy   dx ] [ x-x1 ]
        #    [ s ] = DET  [ -dy1  dx1 ] [ y-y1 ]
        #
        # where DET = (-dx1 * dy + dy1 * dx)
        #
        # if DET is too small, they're parallel
        #
        DET = (-dx1 * dy + dy1 * dx)

        if math.fabs(DET) < DET_TOLERANCE:
            print('parallel')
            return None, None
        # now, the determinant should be OK
        DETinv = 1.0 / DET
        # find the scalar amount along the "self" segment
        r = DETinv * (-dy * (x - x1) + dx * (y - y1))
        # find the scalar amount along the input line
        s = DETinv * (-dy1 * (x - x1) + dx1 * (y - y1))
        # return the average of the two descriptions
        xi = (x1 + r * dx1 + x + s * dx) / 2.0
        yi = (y1 + r * dy1 + y + s * dy) / 2.0
        if print_fulness:
            print('self segment', r)
            print('other segment', s)
        return (round(xi), round(yi)), round(r, 4), round(s, 4)

    def is_between(self, c: 'Point'):
        a = self.p1
        b = self.p2
        cross_product = (c.y - a.y) * (b.x - a.x) - (c.x - a.x) * (b.y - a.y)

        # compare versus epsilon for floating point values, or != 0 if using integers
        if abs(cross_product) > math.e:
            return False

        dot_product = (c.x - a.x) * (b.x - a.x) + (c.y - a.y) * (b.y - a.y)
        if dot_product < 0:
            return False

        squared_length_ba = (b.x - a.x) * (b.x - a.x) + (b.y - a.y) * (b.y - a.y)
        if dot_product > squared_length_ba:
            return False

        return True

    def on_line(self, other: 'Point'):
        if self.vertical:
            if almost_equals(self.p1.x, other.x):
                return True
        else:
            if almost_equals(self.p1.y, other.y):
                return True
        return False

    def __contains__(self, other: {'Line', 'Point'}):
        if type(other) == Line:
            if self.vertical == other.vertical:
                return False
            return self.intersect(other)
        if type(other) == Point:
            return self.is_between(other)
            pass

    def corner(self, other: 'Line'):
        if self.p1 == other.p1 or self.p2 == other.p2 or self.p1 == other.p2:
            return True
        return False

    def connected(self, other: 'Line'):
        return other.p1 in self or other.p2 in self

    def parallel(self, other: 'Line'):
        return self.vertical == other.vertical

    def on_corners(self, other: 'Point'):
        return other == self.p1 or other == self.p2

    def test_intersection(self, other: 'Line'):
        """ prints out a test for checking by hand... """
        print('Testing intersection of:')
        print('\t', self)
        print('\t', other)
        result = self.intersection(other, True)
        print("\t Intersection result =", Point(result[0]))
        print()


class Cell:
    """P1-------P2
        |       |
        |       |
        |       |
        |       |
       P4-------P3
    """
    font = ImageFont.truetype('arial', size=9)

    def __init__(self, p1, p2, p3, p4):
        self.p1: Point = p1
        self.p2: Point = p2
        self.p3: Point = p3
        self.p4: Point = p4
        self.text = ''

    def __repr__(self):
        return 'Cell <{} {}> '.format(self.p1, self.p3)

    @property
    def as_tuple(self):
        return (self.p1.as_tuple, self.p2.as_tuple, self.p3.as_tuple, self.p4.as_tuple)

    def __eq__(self, other: 'Cell'):
        if self.p1 == other.p1 and self.p2 == other.p2 and self.p3 == other.p3 and self.p4 == other.p4:
            return True
        if self.p1 == other.p2 and self.p2 == other.p3 and self.p3 == other.p4 and self.p4 == other.p1:
            return True
        if self.p1 == other.p3 and self.p2 == other.p4 and self.p3 == other.p1 and self.p4 == other.p2:
            return True
        if self.p1 == other.p4 and self.p2 == other.p1 and self.p3 == other.p2 and self.p4 == other.p3:
            return True

    @property
    def center(self):
        x = [p.x for p in [self.p1, self.p2, self.p3, self.p4]]
        y = [p.y for p in [self.p1, self.p2, self.p3, self.p4]]
        centroid = Point(sum(x) / 4, sum(y) / 4)
        return centroid

    def point_inside_polygon(self, point: 'Point', include_edges=True):
        '''
        Test if point (x,y) is inside polygon poly.

        poly is N-vertices polygon defined as
        [(x1,y1),...,(xN,yN)] or [(x1,y1),...,(xN,yN),(x1,y1)]
        (function works fine in both cases)

        Geometrical idea: point is inside polygon if horisontal beam
        to the right from point crosses polygon even number of times.
        Works fine for non-convex polygons.
        '''
        x, y = point.as_tuple
        poly = self.as_tuple
        n = len(poly)
        inside = False

        p1x, p1y = poly[0]
        for i in range(1, n + 1):
            p2x, p2y = poly[i % n]
            if p1y == p2y:
                if y == p1y:
                    if min(p1x, p2x) <= x <= max(p1x, p2x):
                        # point is on horisontal edge
                        inside = include_edges
                        break
                    elif x < min(p1x, p2x):  # point is to the left from current edge
                        inside = not inside
            else:  # p1y!= p2y
                if min(p1y, p2y) <= y <= max(p1y, p2y):
                    xinters = (y - p1y) * (p2x - p1x) / float(p2y - p1y) + p1x

                    if x == xinters:  # point is right on the edge
                        inside = include_edges
                        break

                    if x < xinters:  # point is to the left from current edge
                        inside = not inside

            p1x, p1y = p2x, p2y

        return inside

    def draw(self, canvas: ImageDraw.ImageDraw, color='black'):

        canvas.rectangle((self.p1.as_tuple, self.p3.as_tuple), outline=color)
        if self.text:
            canvas.text((self.p1.x + 3, self.center.y - 5), self.text, fill='black', font=self.font)


class Table:
    font = ImageFont.truetype('arial', size=9)

    def __init__(self, table: List[Cell], skeleton: List[Cell], texts: List[Tuple[str, Point]],
                 canvas: ImageDraw.ImageDraw):
        self.canvas = canvas
        self.texts = texts
        self.skeleton = skeleton
        self.table = table
        self.table_skeleton = {}
        self.global_map = {}
        self.map = {}

    def split_to_2d(self):
        y_list = []
        cell_map = {}
        for cell in self.skeleton:
            if cell.center.y not in y_list:
                y_list.append(cell.center.y)
        y_list.sort()
        for n, y in enumerate(y_list):
            row = filter(lambda c: c.center.y == y, self.skeleton)
            row = list(sorted(row, key=lambda c: c.center.x))
            cell_map[n] = row
        self.table_skeleton = cell_map

    def build_table(self):
        self.split_to_2d()
        for y, row in self.table_skeleton.items():
            self.global_map[y] = {}
            for x, cell in enumerate(row):
                for t_cell in self.table:
                    if t_cell.point_inside_polygon(cell.center):
                        # t_cell.text = "{} {}".format(y, x)
                        self.global_map[y][x] = t_cell

        pass
        for text, p1 in self.texts:
            for cell in self.table:
                if cell.point_inside_polygon(p1):
                    cell.text += text

        for cell in self.table:
            cell.draw(self.canvas)
        # sorted_cells = sorted(self.skeleton, key=lambda c: c.center.y)
        # for s_cell in sorted_cells:
        #     for cell in self.table:
        #         if cell.point_inside_polygon(s_cell.center):
        #             pass


class PDFInterpreter:
    ts = [t / 100.0 for t in range(20)]
    n = 4
    flip_page = False

    @property
    def xsize(self):
        return self.page_size[0]

    @property
    def ysize(self):
        return self.page_size[1]

    def __init__(self, table_node: DataSheetTableNode = None, pdf=None, page: int = None):
        if table_node:
            self.table = table_node
            self.page = self.table.page
            self.content = self.table.get_data()
            self.name = self.table.name.split('.')[0]

        if page and pdf:
            self.page = pdf.pages[page]
            self.content = self.page['/Contents'].getData().decode('cp1251')
            self.name = 'page-{}'.format(page)

        self.page_size = tuple(self.page['/CropBox'][2:])
        self.image = None  # type: Image.Image
        self.canvas = None  # type: ImageDraw.ImageDraw
        self.commands = []
        self.fonts = {}
        self.font_key = ''
        self.prepared = False
        self.font_size = 1
        self.text_cursor = (0, self.ysize)
        self.text_scale_x, self.text_scale_y = 1, 1
        self.text_offset_x, self.text_offset_y = 0, 0
        self.text_leading = 0
        self.text_char_spacing = 0.0
        self.text_word_spacing = 0.0
        self.text_rise = 0

        self.figure_cursor = (0, 0)
        self.figure_scale_x, self.figure_scale_y = 1, 1
        self.figure_offset_x, self.figure_offset_y = 0, 0

        self.lines = []  # type: List[Line]
        self.points = []  # type: List[Point]
        self.skeleton_points = []  # type: List[Point]
        self.skeleton = []  # type: List[Cell]
        self.cells = []  # type: List[Cell]
        self.texts = []  # type: List[(str,Point)]
        self.table = Table(self.cells, self.skeleton, self.texts, self.canvas)
        self.draw = False
        self.useful_content = [(6, 76), (6 + 556, 76 + + 657)]

    def prepare(self):
        self.image = Image.new('RGB', self.page_size, 'white')
        self.canvas = ImageDraw.ImageDraw(self.image)
        self.table.canvas = self.canvas
        self.prepared = True
        for name, data in self.page['/Resources']['/Font'].items():
            font_info = data.getObject()['/FontDescriptor']
            # font_file = font_info['/FontFile2'].getObject().getData()
            self.fonts[str(name)] = font_info['/FontName'].split("+")[-1].split(",")[0].split("-")[0]

    def add_points(self, line: Line):
        if line.p1 not in self.points:
            self.points.append(line.p1)
        if line.p2 not in self.points:
            self.points.append(line.p2)

    def add_skeleton_points(self, line: Line):
        if line.p1 not in self.skeleton_points:
            self.skeleton_points.append(line.p1)
        if line.p2 not in self.skeleton_points:
            self.skeleton_points.append(line.p2)

    def clean_points(self):
        for point in self.points:
            if point.l and point.r and not (point.u or point.d):
                self.points.remove(point)
            if point.u and point.d and not (point.l or point.r):
                self.points.remove(point)

    def build_skeleton(self):
        lines = copy.deepcopy(self.lines)
        temp_point = Point(0, 0)
        temp_point.d = temp_point.u = temp_point.l = temp_point.r = True
        for line1 in lines:
            self.add_skeleton_points(line1)
            for line2 in lines:
                if line1 == line2:
                    continue
                self.add_skeleton_points(line2)
                if line2.vertical == line1.vertical:
                    continue
                if line1.infite_intersect(line2):
                    p1 = Point(line1.infite_intersect(line2))
                    if p1 not in self.skeleton_points:
                        self.skeleton_points.append(p1)

                    for n, p in enumerate(self.skeleton_points):
                        self.skeleton_points[n].copy(temp_point)
                        if p == p1:
                            p1.copy(p)
                            self.skeleton_points[n] = p1
        sorted_y_points = sorted(self.skeleton_points, key=lambda other: other.y)
        for p1 in sorted_y_points:
            p2 = p1.get_right(self.skeleton_points)
            if p2:
                p3 = p2.get_bottom(self.skeleton_points, right=True)
                p4 = p1.get_bottom(self.skeleton_points, left=True)
                if p3 and p4:
                    cell = Cell(p1, p2, p3, p4)
                    if cell not in self.skeleton:
                        self.skeleton.append(cell)
                    else:
                        continue
                    print(p1, p2)
                    print(p4, p3)
                    print('-' * 20)
                    if self.draw:
                        # self.canvas.polygon((p1.as_tuple, p2.as_tuple, p3.as_tuple, p4.as_tuple), fill='gray')
                        cell.draw(self.canvas)
        if self.draw:
            for point in self.skeleton_points:
                point.draw(self.canvas)
        name = self.name
        self.name += '-skeleton'
        self.save()
        self.name = name
        self.canvas.rectangle(((0, 0), self.page_size), 'white')

    def rebuild_table(self):
        for line1 in self.lines:
            self.add_points(line1)
            for line2 in self.lines:
                if line1 == line2:
                    continue
                self.add_points(line2)
                if line1 in line2:
                    line1.test_intersection(line2)
                    xy, _, _ = line1.intersection(line2)
                    p1 = Point(xy)
                    if p1 == line1.p1:  # fixing alignment
                        p1.copy(line1.p1)
                        line1.p1 = p1
                    if p1 == line1.p2:
                        p1.copy(line1.p2)
                        line1.p2 = p1
                    if p1 == line2.p1:
                        p1.copy(line2.p1)
                        line2.p1 = p1
                    if p1 == line2.p2:
                        p1.copy(line2.p2)
                        line2.p2 = p1
                    if p1 not in self.points:
                        self.points.append(p1)
                    for n, p in enumerate(self.points):
                        if p == p1:
                            p1.copy(p)
                            self.points[n] = p1
                    del n
                    p1 = list(filter(lambda p: p == p1, self.points))[0]
                    if line1.is_between(p1):
                        if not line1.on_corners(p1):

                            if line1.vertical:
                                p1.d = True
                                p1.u = True
                            else:
                                p1.r = True
                                p1.l = True
                        elif line1.on_corners(p1):
                            if line1.vertical:
                                if p1 == line1.p1:
                                    p1.d = True
                                else:
                                    p1.u = True
                            else:
                                if p1 == line1.p1:
                                    p1.r = True
                                else:
                                    p1.l = True
        self.clean_points()

        sorted_y_points = sorted(self.points, key=lambda other: other.y)
        for p1 in sorted_y_points:
            if p1.d:
                p2 = p1.get_right(self.points)
                if p2:
                    p3 = p2.get_bottom(self.points, right=True)
                    p4 = p1.get_bottom(self.points, left=True)
                    if p3 and p4:
                        cell = Cell(p1, p2, p3, p4)
                        if cell not in self.cells:
                            self.cells.append(cell)
                        else:
                            continue
                        if self.draw:
                            print(p1, p2)
                            print(p4, p3)
                            print('-' * 20)
                            color = random.choice(list(ImageColor.colormap.keys()))
                            # self.canvas.polygon((p1.as_tuple, p2.as_tuple, p3.as_tuple, p4.as_tuple), fill=color)
                            cell.draw(self.canvas)
                            # cell.center.draw(self.canvas)
        for p in self.points:
            p.draw(self.canvas)
        # for p in random.choices(self.cells,k=20):
        #     color = random.choice(list(ImageColor.colormap.keys()))
        #     p.draw(self.canvas,color)
        name = self.name
        self.name += '-clean'
        self.save()
        self.name = name
        self.canvas.rectangle(((0, 0), self.page_size), 'white')

    def flip_y(self, y):
        if self.flip_page:
            return self.ysize - y
        else:
            return y

    @property
    def new_line(self):
        return self.font.getsize('A')[1]

    @property
    def font(self):
        try:
            return ImageFont.truetype(self.fonts[self.font_key].lower(), int(self.font_size * self.text_scale_x))
        except:
            return ImageFont.truetype('arial', int(self.font_size * self.text_scale_x))

    def draw_rect(self, x, y, w, h):

        if w > 1.0:
            self.canvas.line((x, y, x + w, y), fill='black')
            print('LINE X', x, y)
            self.lines.append(Line(Point(x, y), Point(x + w, y)))
        elif h > 1.0:
            self.canvas.line((x, y, x, y - h), fill='black')
            print('LINE Y', x, y)
            self.lines.append(Line(Point(x, y), Point(x, y - h)))
        else:
            self.canvas.rectangle((x, y, x + w, y - h), fill='black')
            # self.lines.append(Line((x, y), (x, y - h)))
            # self.lines.append(Line((x, y), (x + w, y)))
            print('RECT', x, y)

    def move_cursor_text(self, x=0, y=0):
        xc, yc = self.text_cursor
        self.text_cursor = (xc + x, yc + y)

    @property
    def get_transformed_figure_cursor(self):
        """Returns cursor with offset applied"""
        x, y = self.figure_cursor
        return x + self.figure_offset_x, self.flip_y(y + self.figure_offset_y)

    def apply_transforms_figure(self, x, y):
        return x + self.figure_offset_x, self.flip_y(y + self.figure_offset_y)

    def move_cursor_figure(self, x=0, y=0):
        xc, yc = self.figure_cursor
        self.figure_cursor = (xc + x, yc + y)

    def plot_curve(self, px, py, steps=1000, color=(0)):
        def B(coord, i, j, t):
            if j == 0:
                return coord[i]
            return (B(coord, i, j - 1, t) * (1 - t) +
                    B(coord, i + 1, j - 1, t) * t)

        # img = self.image.load()
        for k in range(steps):
            t = float(k) / (steps - 1)
            x = int(B(px, 0, self.n - 1, t))
            y = int(B(py, 0, self.n - 1, t))
            try:
                self.canvas.point((x, y), fill=color)
                # img[x, y] = color
            except IndexError:
                pass

    def plot_control_points(self, coords, radi=1.2, color=(0)):
        for x, y in coords:
            self.canvas.ellipse((x - radi, y - radi, x + radi, y + radi), color)

    def parse(self):
        if not self.prepared:
            raise Warning('Interpreter isn\'t prepared')
        for line in self.content.split('\n')[1:]:  # type:str
            if '\(' in line:  # temp fix for escaped parentheses
                line = line.replace('\(', ' ')
            if '\)' in line:
                line = line.replace('\)', ' ')
            if '\>' in line:
                line = line.replace('\>', ' ')
            if '\<' in line:
                line = line.replace('\<', ' ')
            if '\[' in line:
                line = line.replace('\[', ' ')
            if '\]' in line:
                line = line.replace('\]', ' ')
            if not line:
                continue
            if line.startswith('/'):
                args = line.split(' ')
                opcode = args[-1]
                args = args[:-1]
                self.commands.append((opcode, args))
                continue
            if DEBUG:
                print(line)
            command = OneOrMore(COMMAND).parseString(line)  # parse line to command
            self.commands.extend(command)

    def render(self):
        text_line = ''
        for n, command in enumerate(self.commands):
            if DEBUG:
                print(command)
            opcode = command[0]  # Command opcode
            args = command[1]  # command args

            if opcode == 'c':
                a1, a2, b1, b2, c1, c2 = args  # bezier points

                a1, a2 = self.apply_transforms_figure(a1, a2)
                b1, b2 = self.apply_transforms_figure(b1, b2)
                oc1, oc2 = c1, c2
                c1, c2 = self.apply_transforms_figure(c1, c2)
                d1, d2 = self.get_transformed_figure_cursor
                self.canvas.line(((d1, d2), (c1, c2)), fill='black', width=1)
                self.figure_cursor = (oc1, oc2)
                print('Drawing C bezier curve at X1:{:.2f} Y1:{:.2f} X3:{:.2f} Y3:{:.2f}'.format(d1, d2, c1, c2))
            if opcode == 'v':
                a1, a2, c1, c2 = args  # bezier points

                a1, a2 = self.apply_transforms_figure(a1, a2)
                oc1, oc2 = c1, c2
                c1, c2 = self.apply_transforms_figure(c1, c2)
                d1, d2 = self.get_transformed_figure_cursor
                self.canvas.line(((d1, d2), (c1, c2)), fill='black', width=1)
                self.figure_cursor = (oc1, oc2)
                print('Drawing V bezier curve at X1:{:.2f} Y1:{:.2f} X3:{:.2f} Y3:{:.2f}'.format(d1, d2, c1, c2))
            if opcode == 'y':
                a1, a2, c1, c2 = args  # bezier points
                oc1, oc2 = c1, c2
                a1, a2 = self.apply_transforms_figure(a1, a2)
                c1, c2 = self.apply_transforms_figure(c1, c2)
                d1, d2 = self.get_transformed_figure_cursor
                self.canvas.line(((d1, d2), (c1, c2)), fill='black', width=1)
                self.figure_cursor = (oc1, oc2)
                print('Drawing Y bezier curve at X1:{:.2f} Y1:{:.2f} X3:{:.2f} Y3:{:.2f}'.format(d1, d2, c1, c2))
            if opcode == 'l':
                c1, c2 = args  # bezier points
                oc1, oc2 = c1, c2
                c1, c2 = self.apply_transforms_figure(c1, c2)
                d1, d2 = self.get_transformed_figure_cursor
                self.canvas.line(((d1, d2), (c1, c2)), fill='black', width=1)
                self.figure_cursor = (oc1, oc2)
                print('Drawing line           at X1:{:.2f} Y1:{:.2f} X3:{:.2f} Y3:{:.2f}'.format(d1, d2, c1, c2))

            if opcode == 'f':
                pass

            if opcode == 'csn':
                self.color = tuple(args)

            if opcode == 'cm':
                scale_x, shear_x, shear_y, scale_y, offset_x, offset_y = args
                self.figure_scale_x = scale_x
                self.figure_scale_y = scale_y
                self.figure_offset_x = offset_x
                self.figure_offset_y = offset_y
                print('Transformed FIGURE cursor now at', self.get_transformed_figure_cursor)

            if opcode == 're':  # RENDER BOX
                x, y, w, h = args  # absolute coordinated, doesn't require any transformations
                # fill = 0 if commands[n + 1][0] == 'f' else None
                fill = None
                print('Drawing box at X:{} Y:{} W:{} H:{}'.format(x, y, w, h))
                if self.useful_content[0][1] < self.flip_y(y) < self.useful_content[1][1]:
                    self.draw_rect(x, self.flip_y(y), w, h)

            if opcode == 'BT':
                print('New text block')
                self.text_cursor = (0, self.ysize)
                self.color = (0, 0, 0)

            if opcode == 'ET':
                print('End text block')
                self.text_cursor = (0, self.ysize)

            if opcode == 'Tf':
                font, font_size = args
                font_size = int(font_size)
                print('Loading font', font, font_size)
                self.font_size = font_size
                self.font_key = font

            if opcode == 'TD':  # MOVE CURSOR
                x, y = args  # TD arguments
                x *= self.text_scale_x
                y *= self.text_scale_y

                if self.flip_page:
                    self.text_leading = -y
                    self.move_cursor_text(x, -y)
                else:
                    self.text_leading = y
                    self.move_cursor_text(x, y)
                print('Moving cursor by X:{} Y:{}, new cursor'.format(x, y), self.text_cursor)
                # self.text_cursor = (x, y)
            if opcode == 'Td':
                x, y = args  # TD arguments
                x *= self.text_scale_x
                y *= self.text_scale_y
                if self.flip_page:
                    self.move_cursor_text(x, -y)
                else:
                    self.move_cursor_text(x, y)
                # cx,cy = self.text_cursor
                # self.text_cursor = (cx*x,cy*y)
                print('Moving cursor by X:{} Y:{}, new cursor'.format(x, y), self.text_cursor)
                # self.text_cursor = (x, y)

            if opcode == 'TL':
                self.text_leading = args[0]
                print('Setting text leading to', args[0])

            if opcode == 'Tc':
                self.text_char_spacing = args[0]
                print('Setting text char spacing to', args[0])

            if opcode == 'Tw':
                self.text_word_spacing = args[0]
                print('Setting text word spacing to', args[0])

            if opcode == 'Ts':
                self.text_rise = args[0]
                print('Setting text word rise to', args[0])

            if opcode == 'Tm':  # STORE MATRIX
                scale_x, shear_x, shear_y, scale_y, offset_x, offset_y = args
                self.text_scale_x = scale_x
                self.text_scale_y = scale_y
                self.text_offset_x = offset_x
                self.text_offset_y = offset_y
                self.text_cursor = (offset_x, self.flip_y(offset_y))
                # print('TM', args)
                print('Transformed TEXT cursor now at', self.text_cursor, self.text_scale_x)
                # print('Transformed TEXT cursor now at', self.get_transformed_text_cursor)

            if opcode == 'TJ':  # RENDER TEXT
                orig_cursor = self.text_cursor
                new_line = self.new_line
                text_lines = []
                if self.flip_page:
                    self.move_cursor_text(0, -new_line / 1.3)

                for text_arg in args:
                    text = text_arg[0]

                    x1 = (-text_arg[1] / 1000) * self.text_scale_x
                    if x1>5:
                        self.texts.append((text_line, Point(self.text_cursor)))
                        text_line = ""
                    self.move_cursor_text(x1)
                    print('Printing "{}" at'.format(text), self.text_cursor)
                    words = text.split(' ')
                    for n, word in enumerate(words):
                        space, _ = self.font.getsize(' ')
                        for char in word:
                            text_line+=char
                            x2, y2 = self.font.getsize(char)
                            self.canvas.text(self.text_cursor, char, font=self.font, fill='black')
                            self.move_cursor_text(x2 + (self.text_char_spacing * self.text_scale_x))
                            if self.text_char_spacing * self.text_scale_x>5:
                                self.texts.append((text_line, Point(self.text_cursor)))
                                text_line = ""
                        self.move_cursor_text(self.text_word_spacing * self.text_scale_x)
                        if self.text_word_spacing * self.text_scale_x>5:
                            self.texts.append((text_line, Point(self.text_cursor)))
                            text_line = ""
                        if 1 < len(words) != n + 1:
                            self.move_cursor_text(space)

                if text_line:
                    self.texts.append((text_line, Point(self.text_cursor)))
                    text_line = ""
                self.text_cursor = orig_cursor

            if opcode == 'T*':
                # _, new_line = self.font.getsize('A')
                if self.flip_page:
                    self.move_cursor_text(0, self.text_leading)
                else:
                    self.move_cursor_text(0, self.text_leading)
                # self.texts.append(("\n",Point(self.text_cursor)))
            if opcode == 'Tj':
                text = args[0]
                new_line = self.new_line
                if self.flip_page:
                    self.move_cursor_text(0, -new_line / 1.3)
                print('Printing "{}" at'.format(text), self.text_cursor)
                self.texts.append((text, Point(self.text_cursor)))
                self.canvas.text(self.text_cursor, text, font=self.font, fill='black')
                if self.flip_page:
                    self.move_cursor_text(0, new_line / 1.3)
        name = self.name
        self.name += '-text'
        self.save()
        self.name = name

    def save(self, path=None):
        if not self.prepared:
            raise Warning('Interpreter isn\'t prepared')
        if path:
            path = (Path(path) / self.name).with_suffix('.png')
        else:
            path = (Path.cwd() / self.name).with_suffix('.png')
        with path.open('wb') as fp:
            self.image.save(fp)


if __name__ == '__main__':
    pdf = DataSheet('stm32L431')
    table = 2
    print(pdf.table_root.childs[table])
    # for table in pdf.table_root.childs:
    #     a = PDFInterpreter(table)
    #     a = PDFInterpreter(pdf.table_root.childs[1])
    #     # print(a.node.get_data())
    #     a.prepare()
    #     a.render()
    #     a.save()
    pdf_interpreter = PDFInterpreter(pdf=pdf.pdf_file, page=13)
    pdf_interpreter.draw = True
    # pdf_interpreter = PDFInterpreter(pdf.table_root.childs[table])
    pdf_interpreter.flip_page = True
    # print(pdf_interpreter.content)
    pdf_interpreter.prepare()
    pdf_interpreter.parse()
    # pdf_interpreter.save()
    pdf_interpreter.render()
    pdf_interpreter.build_skeleton()
    pdf_interpreter.rebuild_table()
    pdf_interpreter.table.build_table()
    pdf_interpreter.save()
