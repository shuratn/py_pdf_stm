from functools import partial

from DumpPDFText import *
from PIL import Image, ImageDraw
from pathlib import Path
import pyparsing
from pyparsing import *
DEBUG = True

def to_int_float(string):
    if '.' in string:
        return float(string)
    else:
        return int(string)


def tt(*a, name="OPCODE"):
    string = a[0]
    offset = a[1] or 1
    from_ = 0
    if type(a[2]) == int:
        from_ = a[2]
        a=a[3:]
    print('Parsing',name,':')
    # print('Searching for',a[0])
    print(from_,offset)
    print('"{}"'.format(string))
    print(('-'*(offset))+'^')
    print(a[2:])
    print()
    b= 5


OPCODE = Word(alphas+'*')
OPCODE.debug = DEBUG
OPCODE.debugActions = (tt, tt, tt)
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


def parse_number(string):
    string = string[0]
    return to_int_float(string)

dd = partial(tt, name='NUMBER')
NUMBER.debug=DEBUG
NUMBER.debugActions = (dd, dd, dd)


NUMBER.setParseAction(parse_number)
TEXT = LBR + Word(printables).leaveWhitespace() + RBR
TEXT_ARGS = Optional(NUMBER) + TEXT


def parse_text_args(text):
    if len(text) == 2:
        return text[1], text[0]
    return (text[0],)


TEXT_ARGS.setParseAction(parse_text_args)

TEXT_ARGS.debug = DEBUG
dd = partial(tt, name='TEXT_ARGS')
TEXT_ARGS.debugActions = (dd, dd, dd)

# TEXT_ARGS = Regex(r'((-?(\d+)?\.?(\d*\([\w\d\s]+\))))')
SPACE = Literal(' ').suppress()
COMMAND = ((LSBR + OneOrMore(TEXT_ARGS) + RSBR) + OPCODE) | (OneOrMore(NUMBER) + OPCODE) | OPCODE

COMMAND.debug = DEBUG
dd = partial(tt, name='COMMAND')
COMMAND.debugActions = (dd, dd, None)



# a = '-29964.8'
a = '(T)72.3(a)5.5(ble 4. ST)6(M32)5.5(L)0(43)5.5(1xx)5.5( )-6(mo)6(des)5.5( )-6(ov)5.5(erv)5.5(i)-1.7(e)5.5(w)4.3( )'
# print(NUMBER.parseString(a))
print(OneOrMore(TEXT_ARGS).parseString(a))
exit(1)


class PDFInterpreter:
    page_size = (1024, 2048)

    def __init__(self, table_node: DataSheetTableNode):
        self.node = table_node
        self.image = None  # type: Image.Image
        self.canvas = None  # type: ImageDraw.ImageDraw
        self.prepared = False
        self.font_size = 1
        self.char_spacing = 1
        self.word_spacing = 1

    def prepare(self):
        self.image = Image.new('L', self.page_size, (255,))
        self.canvas = ImageDraw.ImageDraw(self.image)
        self.prepared = True

    def render(self):
        if not self.prepared:
            raise Warning('Interpreter isn\'t prepared')
        self.canvas.line(((100, 5), (150, 1024)), width=15)
        for line in self.node.get_table_data().split('\n'):  # type:str
            if line.startswith('/'):
                continue
            print(line)
            print(COMMAND.parseString(line))

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
    a = PDFInterpreter(pdf.table_root.childs[3])
    a.prepare()
    a.render()
    a.save()
