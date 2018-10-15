import json
from pprint import pprint
from typing import List, Dict, Any
import re


class WithParent:
    parent = None

    def register(self, obj: 'WithParent'):
        obj.parent = self


class Pin(WithParent):

    equality_dict = {
        'LPUART':'UART',
        'USART':'UART',
    }

    parent: 'PinManager'

    def __init__(self, pin_id: str, functions: List[str], pin_type: str, package: str) -> None:
        """
        :type pin_type: str IO or S
        :type functions: List[str] Array of pin functions
        :type pin_id: str Name\Id of pin
        """
        self.pin_id = pin_id
        self.functions = functions
        self.pin_type = pin_type
        self.package = package
        self.pairs = []  # type: List[Pin]

    def extract_pin_info(self, pin_func: str):
        if '_' in pin_func:
            res = re.match('(?P<main_name>[a-zA-Z2]+)(?P<id>(\d{1,3})?)_(?P<sub_type>[a-zA-Z]+)_?(?P<id2>(\d{1,3})?)',
                           pin_func, re.IGNORECASE)
            if res:
                res = res.groupdict()
                # print(res)
                module_name = res.get('main_name')
                module_name = self.equality_dict.get(module_name,module_name)
                module_sub_func = res.get('sub_type')
                if res.get('id') == '':
                    module_id = res.get('id2', '0')
                else:
                    module_id = res.get('id', '0')
                return module_name, module_sub_func, module_id
        return pin_func,'UNK',0

    def have_func(self, func_name):
        for func in self.functions:
            func_,_,_ = self.extract_pin_info(func)
            func_ = self.equality_dict.get(func_,func_)
            if func_name.upper() in func_.upper():
                return func
        else:
            return False

    def get_pair(self, func_name):
        mod_name, mod_sub, mod_id = None, None, None
        func_name = self.have_func(func_name)
        if func_name:
            mod_name, mod_sub, mod_id = self.extract_pin_info(func_name)
        else:
            return None
        for pin in self.parent.pins[self.package]:
            pair_func_name = pin.have_func(mod_name)
            if pair_func_name:
                pair_mod_name, pair_mod_sub, pair_mod_id = self.extract_pin_info(pair_func_name)
                if pair_func_name != func_name and pair_mod_id != mod_id:
                    continue
                if pin == self and pin not in self.pairs:
                    continue
                if func_name ==pair_mod_name:
                    continue
                self.pairs.append(pin)
        return self.pairs

    def __repr__(self):
        return '<Pin-{} {} {}>'.format(self.pin_id, self.pin_type, '|'.join(self.functions))


class PinManager(WithParent):

    def __init__(self, pinout: Dict[str, Dict[str, Any]]) -> None:
        """

        :type pinout: Dict[str, Dict[str, str]]
        """
        self.packages_pinout = pinout  # type: Dict[str, Dict[str, Any]]
        self.pins = {}  # type: Dict[str,List[Pin]]
        self.already_used_pins = []  # type: List[str]

    def read_pins(self):
        for package, pinout in self.packages_pinout.items():
            self.pins[package] = []
            for pin_id, pin_data in pinout['pins'].items():
                pin = Pin(pin_id, pin_data['functions'], pin_data['type'], package)
                self.register(pin)
                self.pins[package].append(pin)

    def get_pins_by_func(self, func_name, package):
        pins = []  # type: List[Pin]
        for pin in self.pins[package]:
            if pin.have_func(func_name):
                pins.append(pin)
        return pins


if __name__ == '__main__':
    with open('pins2.json') as fp:
        pins = json.load(fp)
    a = PinManager(pins)
    a.read_pins()
    # pin = a.pins['LQFP100'][15]
    pin = a.pins['LQFP64'][5]
    print('The pairs of', pin, 'is', pin.get_pair('TSI'))
    print('Pins with TSI:')
    pprint(a.get_pins_by_func('TSI', 'LQFP64'))
    # pprint(a.pins)
