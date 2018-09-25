import math
from functools import partial

from DumpPDFText import *
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import io
from pyparsing import *

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
    return (text[0], 0.0)


def parse_command(text):
    opcode = text[-1]
    args = text[:-1]
    # print(opcode,args)
    return (opcode, args)


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
class Line:

    def __init__(self, xy1, xy2):
        x, y = xy1
        cx, cy = xy2

        self.x = math.ceil(x)
        self.y = math.ceil(y)
        self.cx = math.ceil(cx)
        self.cy = math.ceil(cy)
        self.vertical = self.x == self.cx

    def draw(self, canvas: ImageDraw.ImageDraw,color='blue'):
        x,y = self.x - 5, self.y - 5
        cx,cy = self.cx + 5, self.cy + 5

        canvas.line(((x,y),(cx,cy)), color)

    @property
    def as_tuple(self):
        return ((self.x, self.y), (self.cx, self.cy))

    def intersect(self, other: 'Line'):
        """ this returns the intersection of Line(pt1,pt2) and Line(ptA,ptB)
              returns a tuple: (xi, yi, valid, r, s), where
              (xi, yi) is the intersection
              r is the scalar multiple such that (xi,yi) = pt1 + r*(pt2-pt1)
              s is the scalar multiple such that (xi,yi) = pt1 + s*(ptB-ptA)
                  valid == 0 if there are 0 or inf. intersections (invalid)
                  valid == 1 if it has a unique intersection ON the segment    """
        pt1 = self.x-5, self.y-5
        pt2 = self.cx+5, self.cy+5
        ptA = other.x-5, other.y-5
        ptB = other.cx+5, other.cy+5

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

        if math.fabs(DET) < DET_TOLERANCE: return False
        # now, the determinant should be OK
        DETinv = 1.0 / DET
        # find the scalar amount along the "self" segment
        r = DETinv * (-dy * (x - x1) + dx * (y - y1))
        # find the scalar amount along the input line
        s = DETinv * (-dy1 * (x - x1) + dx1 * (y - y1))
        # return the average of the two descriptions
        xi = (x1 + r * dx1 + x + s * dx) / 2.0
        yi = (y1 + r * dy1 + y + s * dy) / 2.0
        print('self segment', r)
        print('other segment', s)
        if r > 0 and s > 0:
            return True
        return False

    def intersection(self, other: 'Line'):
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

    def __contains__(self, other: 'Line'):
        return self.intersect(other)

    def testIntersection(self, other: 'Line'):
        """ prints out a test for checking by hand... """
        result = self.intersect(other)
        print("    Intersection result =", result)
        print()


class Point:
    r = 4
    hr = r / 2

    def __init__(self, xy):
        self.x, self.y = xy

    @property
    def as_tuple(self):
        return (self.x, self.y)

    def draw(self, canvas: ImageDraw.ImageDraw, color='red'):
        canvas.ellipse((self.x - self.hr, self.y - self.hr, self.x + self.hr, self.y + self.hr), fill=color)

    def points_to_right(self, other_points: List['Point']):
        sorted_other_points = sorted(other_points, key=lambda other: other.y)
        filtered_other_points = filter(lambda other: other != self and other.y == self.y and self.x < other.x,
                                       sorted_other_points)
        return filtered_other_points


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

        self.page_size = self.page.getObject().cropBox[2:]
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
        self.useful_content = [(6, 76), (6 + 556, 76 + + 657)]

    def prepare(self):
        self.image = Image.new('RGB', self.page_size, 'white')
        self.canvas = ImageDraw.ImageDraw(self.image)
        self.prepared = True
        for name, data in self.page['/Resources']['/Font'].items():
            font_info = data.getObject()['/FontDescriptor']
            # font_file = font_info['/FontFile2'].getObject().getData()
            self.fonts[str(name)] = font_info['/FontName'].split("+")[-1].split(",")[0].split("-")[0]

    def rebuild_table(self):
        for line1 in self.lines:
            for line2 in self.lines:
                if line1 == line2:
                    continue
                line1.draw(self.canvas, color='cyan')
                line2.draw(self.canvas, color='cyan')
                self.save()
                if line1 in line2:
                    line1.draw(self.canvas)
                    line2.draw(self.canvas)
                    line1.testIntersection(line2)
                    x, y = line1.intersection(line2)
                    point = Point((x, y))
                    self.points.append(point)
                    point.draw(self.canvas)
                else:
                    pass

                pass
                self.save()
                self.canvas.rectangle(((0,0),tuple(self.page_size)),fill='white')

        #             # point.draw(self.canvas)

        # for p1 in self.points:
        #     ps = p1.points_to_right(self.points)
        #
        #     if ps:
        #         p1.draw(self.canvas)
        #         [p.draw(self.canvas, 'green') for p in ps]
        #         return
        # for p2 in self.points:
        #     for p3 in self.points:
        #         for p4 in self.points:
        #             if p1 == p2 or p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4 or p3 == p4:
        #                 continue

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
            # self.canvas.line((x, y, x + w, y), fill='blue')
            print('LINE X', x, y)
            self.lines.append(Line((x, y), (x + w, y)))
        elif h > 1.0:
            # self.canvas.line((x, y, x, y - h), fill='red')
            print('LINE Y', x, y)
            self.lines.append(Line((x, y), (x, y - h)))
        else:
            # self.canvas.rectangle((x, y, x + w, y - h), fill='green')
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
        for n, command in enumerate(self.commands):
            if DEBUG:
                print(command)
            opcode = command[0]  # Command opcode
            args = command[1]  # command args

            # if opcode == 'c':
            #     a1, a2, b1, b2, c1, c2 = args  # bezier points
            #
            #     a1, a2 = self.apply_transforms_figure(a1, a2)
            #     b1, b2 = self.apply_transforms_figure(b1, b2)
            #     oc1, oc2 = c1, c2
            #     c1, c2 = self.apply_transforms_figure(c1, c2)
            #     d1, d2 = self.get_transformed_figure_cursor
            #     self.canvas.line(((d1, d2), (c1, c2)), fill=(0,), width=1)
            #     self.figure_cursor = (oc1, oc2)
            #     print('Drawing C bezier curve at X1:{:.2f} Y1:{:.2f} X3:{:.2f} Y3:{:.2f}'.format(d1, d2, c1, c2))
            # if opcode == 'v':
            #     a1, a2, c1, c2 = args  # bezier points
            #
            #     a1, a2 = self.apply_transforms_figure(a1, a2)
            #     oc1, oc2 = c1, c2
            #     c1, c2 = self.apply_transforms_figure(c1, c2)
            #     d1, d2 = self.get_transformed_figure_cursor
            #     self.canvas.line(((d1, d2), (c1, c2)), fill=(0,), width=1)
            #     self.figure_cursor = (oc1, oc2)
            #     print('Drawing V bezier curve at X1:{:.2f} Y1:{:.2f} X3:{:.2f} Y3:{:.2f}'.format(d1, d2, c1, c2))
            # if opcode == 'y':
            #     a1, a2, c1, c2 = args  # bezier points
            #     oc1, oc2 = c1, c2
            #     a1, a2 = self.apply_transforms_figure(a1, a2)
            #     c1, c2 = self.apply_transforms_figure(c1, c2)
            #     d1, d2 = self.get_transformed_figure_cursor
            #     self.canvas.line(((d1, d2), (c1, c2)), fill=(0,), width=1)
            #     self.figure_cursor = (oc1, oc2)
            #     print('Drawing Y bezier curve at X1:{:.2f} Y1:{:.2f} X3:{:.2f} Y3:{:.2f}'.format(d1, d2, c1, c2))
            # if opcode == 'l':
            #     c1, c2 = args  # bezier points
            #     oc1, oc2 = c1, c2
            #     c1, c2 = self.apply_transforms_figure(c1, c2)
            #     d1, d2 = self.get_transformed_figure_cursor
            #     self.canvas.line(((d1, d2), (c1, c2)), fill=(0,), width=1)
            #     self.figure_cursor = (oc1, oc2)
            #     print('Drawing line           at X1:{:.2f} Y1:{:.2f} X3:{:.2f} Y3:{:.2f}'.format(d1, d2, c1, c2))
            #
            # if opcode == 'f':
            #     pass
            #
            # if opcode == 'csn':
            #     self.color = tuple(args)

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

            # if opcode == 'BT':
            #     print('New text block')
            #     self.text_cursor = (0, self.ysize)
            #     self.color = (0, 0, 0)
            #
            # if opcode == 'ET':
            #     print('End text block')
            #     self.text_cursor = (0, self.ysize)
            #
            # if opcode == 'Tf':
            #     font, font_size = args
            #     font_size =int(font_size)
            #     print('Loading font', font, font_size)
            #     self.font_size = font_size
            #     self.font_key = font
            #
            # if opcode == 'TD':  # MOVE CURSOR
            #     x, y = args  # TD arguments
            #     x *= self.text_scale_x
            #     y *= self.text_scale_y
            #
            #     if self.flip_page:
            #         self.text_leading = -y
            #         self.move_cursor_text(x, -y)
            #     else:
            #         self.text_leading = y
            #         self.move_cursor_text(x, y)
            #     print('Moving cursor by X:{} Y:{}, new cursor'.format(x, y), self.text_cursor)
            #     # self.text_cursor = (x, y)
            # if opcode == 'Td':
            #     x, y = args  # TD arguments
            #     x *= self.text_scale_x
            #     y *= self.text_scale_y
            #     if self.flip_page:
            #         self.move_cursor_text(x, -y)
            #     else:
            #         self.move_cursor_text(x, y)
            #     # cx,cy = self.text_cursor
            #     # self.text_cursor = (cx*x,cy*y)
            #     print('Moving cursor by X:{} Y:{}, new cursor'.format(x, y), self.text_cursor)
            #     # self.text_cursor = (x, y)
            #
            # if opcode == 'TL':
            #     self.text_leading = args[0]
            #     print('Setting text leading to', args[0])
            #
            # if opcode == 'Tc':
            #     self.text_char_spacing = args[0]
            #     print('Setting text char spacing to', args[0])
            #
            # if opcode == 'Tw':
            #     self.text_word_spacing = args[0]
            #     print('Setting text word spacing to', args[0])
            #
            # if opcode == 'Ts':
            #     self.text_rise = args[0]
            #     print('Setting text word rise to', args[0])
            #
            # if opcode == 'Tm':  # STORE MATRIX
            #     scale_x, shear_x, shear_y, scale_y, offset_x, offset_y = args
            #     self.text_scale_x = scale_x
            #     self.text_scale_y = scale_y
            #     self.text_offset_x = offset_x
            #     self.text_offset_y = offset_y
            #     self.text_cursor = (offset_x, self.flip_y(offset_y))
            #     # print('TM', args)
            #     print('Transformed TEXT cursor now at', self.text_cursor,self.text_scale_x)
            #     # print('Transformed TEXT cursor now at', self.get_transformed_text_cursor)
            #
            # if opcode == 'TJ':  # RENDER TEXT
            #     orig_cursor = self.text_cursor
            #     new_line = self.new_line
            #     if self.flip_page:
            #         self.move_cursor_text(0, -new_line / 1.3)
            #     for text_arg in args:
            #         text = text_arg[0]
            #         xt, yt = self.font.getsize(text)  # text dimensions
            #
            #         x1 = (-text_arg[1] / 1000) * self.text_scale_x
            #
            #         # x1+=self.word_spacing
            #         self.move_cursor_text(x1)
            #         print('Printing "{}" at'.format(text), self.text_cursor)
            #         if self.text_word_spacing!=0.0:
            #             for word in text.split(' '):
            #                 if self.text_char_spacing!=0.0:
            #                     for char in word:
            #                         x2,y2 = self.font.getsize(char)
            #                         self.canvas.text(self.text_cursor, char, font=self.font)
            #                         self.move_cursor_text(x2+(self.text_char_spacing*self.text_scale_x))
            #                 self.move_cursor_text(self.text_word_spacing * self.text_scale_x)
            #         else:
            #             self.canvas.text(self.text_cursor, text, font=self.font)
            #             self.move_cursor_text(xt)
            #     self.text_cursor = orig_cursor
            #
            # if opcode == 'T*':
            #     # _, new_line = self.font.getsize('A')
            #     if self.flip_page:
            #         self.move_cursor_text(0, self.text_leading)
            #     else:
            #         self.move_cursor_text(0, self.text_leading)
            # if opcode == 'Tj':
            #     text = args[0]
            #     new_line = self.new_line
            #     if self.flip_page:
            #         self.move_cursor_text(0, -new_line / 1.3)
            #     # text = text.encode("utf-8").decode('latin-1', 'ignore')  # removing unprintable chars
            #     xt, yt = self.font.getsize(text)  # text dimensions
            #     print('Printing "{}" at'.format(text), self.text_cursor)
            #     self.canvas.text(self.text_cursor, text, font=self.font)
            #     if self.flip_page:
            #         self.move_cursor_text(0, new_line / 1.3)

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
    a = PDFInterpreter(pdf=pdf.pdf_file, page=13)
    # a = PDFInterpreter(pdf.table_root.childs[table])
    a.flip_page = True
    print(a.content)
    a.prepare()
    a.parse()
    a.render()
    a.rebuild_table()
    a.save()
