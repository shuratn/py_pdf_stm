from functools import partial

from DumpPDFText import *
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import pyparsing
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


OPCODE = Word(alphas + '*')
DOT = Literal('.')
LBR = Literal("(").suppress()
RBR = Literal(")").suppress()
LSBR = Literal("[").suppress()
RSBR = Literal("]").suppress()
PLUSORMINUS = Literal('+') | Literal('-')
OPLUSORMINUS = Optional(PLUSORMINUS)

NUMBERS = Word(nums)
NUMBER = Combine(OPLUSORMINUS + NUMBERS + DOT + NUMBERS) | Combine(OPLUSORMINUS + DOT + NUMBERS) | Combine(
    OPLUSORMINUS + NUMBERS)
NUMBER.setParseAction(parse_number)

TEXT = LBR + Word(alphanums + ' .\\/&!@#$%^-=+*µ_,?;:®Ђ™°"\'').leaveWhitespace() + RBR

TEXT_ARGS = Optional(NUMBER) + TEXT
TEXT_ARGS.setParseAction(parse_text_args)

# TEXT_ARGS = Regex(r'((-?(\d+)?\.?(\d*\([\w\d\s]+\))))')
SPACE = Literal(' ').suppress()
COMMAND = ((LSBR + OneOrMore(TEXT_ARGS) + RSBR) + OPCODE) | (OneOrMore(NUMBER) + OPCODE) | TEXT + OPCODE | OPCODE

if DEBUG:
    OPCODE.debug = DEBUG
    OPCODE.debugActions = (debug_print, debug_print, debug_print)

    dd = partial(debug_print, name='NUMBER')
    NUMBER.debug = DEBUG
    NUMBER.debugActions = (dd, dd, dd)

    dd = partial(debug_print, name='TEXT')
    TEXT.debug = DEBUG
    TEXT.debugActions = (dd, dd, dd)

    dd = partial(debug_print, name='TEXT_ARGS')
    TEXT_ARGS.debug = DEBUG
    TEXT_ARGS.debugActions = (dd, dd, dd)

    COMMAND.debug = DEBUG
    dd = partial(debug_print, name='COMMAND')
    COMMAND.debugActions = (dd, dd, None)


# a = '-29964.8'
# a = '(STM32)'
# # print(NUMBER.parseString(a))
# print(TEXT.parseString(a))
# exit(1)


class PDFInterpreter:
    page_size = (2048, 2048)

    def __init__(self, table_node: DataSheetTableNode):
        self.node = table_node
        self.image = None  # type: Image.Image
        self.canvas = None  # type: ImageDraw.ImageDraw
        self.font = ImageFont.truetype('arial')
        self.prepared = False
        self.font_size = 1
        self.char_spacing = 1
        self.word_spacing = 1
        self.cursor = (0, self.page_size[1] // 2)
        self.scale_x, self.scale_y = 1, 1
        self.offset_x, self.offset_y = 0, 0

    def prepare(self):
        self.image = Image.new('L', self.page_size, (255,))
        self.canvas = ImageDraw.ImageDraw(self.image)
        self.prepared = True
        # x,y = self.cursor
        # self.canvas.ellipse((x,y,x+50,y+50))
        # self.save()

    @property
    def get_transformed_cursor(self):
        """Returns cursor with offset applied"""
        x, y = self.cursor
        return x + self.offset_x, y + self.offset_y

    def render(self):
        if not self.prepared:
            raise Warning('Interpreter isn\'t prepared')
        # self.canvas.line(((100, 5), (150, 1024)), width=15)
        commands = []
        for line in self.node.get_table_data().split('\n'):  # type:str
            if '\(' in line:  # temp fix for escaped parentheses
                line = line.replace('\(', ' ')
            if '\)' in line:
                line = line.replace('\)', ' ')
            if line.startswith('/') or not line:  # ignoring keywords
                continue
            # print(line)
            command = COMMAND.parseString(line)  # parse line to command
            commands.append(command)
        for n, command in enumerate(commands):
            print(command)
            opcode = command[-1]  # Command opcode
            args = command[:-1]  # command args
            if opcode == 're':  # RENDER BOX
                x, y, w, h = command[:4]
                # fill = 128 if commands[n+1][0]=='f' else None
                fill = None
                x1, y1 = 0, 0
                # x1, y1 = self.get_transformed_cursor
                x += x1
                y += y1
                self.canvas.rectangle((x, y - h, w, -h), fill)
                print('Drawing box at', x, y - h, w, -h)
            if opcode == 'TD':  # MOVE CURSOR
                print(command)
                x, y = args
                y1, x1 = self.cursor
                x, y = x + x1, y + y1
                self.cursor = (x, y)
                self.canvas.point(self.cursor)
                print('Cursor now at', self.cursor)

            if opcode == 'Tm':  # STORE MATRIX
                scale_x, shear_x, shear_y, scale_y, offset_x, offset_y = args
                self.scale_x = scale_x
                self.scale_y = scale_y
                self.offset_x = offset_x
                self.offset_y = offset_y
                print('TM', args)

            if opcode == 'TJ':  # RENDER TEXT
                print(command)
                for text_arg in args:
                    x, y = self.get_transformed_cursor

                    if type(text_arg) == tuple:
                        x -= text_arg[1]
                        # y -= text_arg[1] # depends on render mode

                        text = text_arg[0]
                    else:
                        raise Exception(str(text_arg))
                    text = text.encode("utf-8").decode('latin-1', 'ignore')
                    print('Printing "{}" at'.format(text), x, y)
                    self.font.size = self.scale_x
                    self.canvas.text((x, y), text, font=self.font)
                    # self.save()
                    a = 5
                    # print(text_arg)

    def save(self, path=None):
        if not self.prepared:
            raise Warning('Interpreter isn\'t prepared')
        if path:
            path = (Path(path) / self.node.table_name).with_suffix('.png')
        else:
            path = (Path.cwd() / self.node.table_name).with_suffix('.png')
        with path.open('wb') as fp:
            self.image.save(fp)


if __name__ == '__main__':
    pdf = DataSheet('stm32L431')
    print(pdf.table_root.childs[3])
    a = PDFInterpreter(pdf.table_root.childs[3])
    a.prepare()
    a.render()
    a.save()
