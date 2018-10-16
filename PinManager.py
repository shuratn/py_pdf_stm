import json
from pprint import pprint
from typing import List, Dict, Any
import re

from Utils import is_dict


class WithParent:
    parent = None

    def register(self, obj: 'WithParent'):
        obj.parent = self


class Pin(WithParent):
    equality_dict = {
        'LPUART': 'UART',
        'USART': 'UART',
        'TSC': 'TSI',
        'COMP': 'ACMP',
        'ACMP': 'CMP',
        'PTA': 'GPIO',
        'PTB': 'GPIO',
        'PTC': 'GPIO',
        'PTD': 'GPIO',
        'PTE': 'GPIO',
        'XTAL0': 'OSC_IN',
        'EXTAL0': 'OSC_OUT',
    }
    equality_sub_dict = {
        'SOUT': 'MOSI',
        'SIN': 'MISO',
        'SCK': 'SCLK',
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
        if pin_type == 'S':
            self.functions = []

    def extract_pin_info(self, pin_func: str):
        pin_func = self.equality_dict.get(pin_func,pin_func)
        if self.pin_type == 'S':
            return 'SOURCE', 'SOURCE', '0', '0'
        if 'PT' in pin_func:
            res = re.match('(?P<main_name>[a-zA-Z]+)(?P<id>(\d{1,3})?)', pin_func, re.IGNORECASE)
            if res:
                res_dict = res.groupdict()
                module_name = res_dict.get('main_name')
                module_id = res_dict.get('id')
                module_name = self.equality_dict.get(module_name, module_name)
                return module_name, 'GPIO', module_id, 0
        if 'TSI' in pin_func or 'TSC' in pin_func:
            module_name = 'TSI'
            module_sub_func = 'IN'
            group_id = pin_func.split('_')[1]
            pin_id = pin_func[-1]
            return module_name, module_sub_func, group_id, pin_id
        if 'OSC' in pin_func:
            module_name, module_sub_func = pin_func.split('_', maxsplit=1)
            group_id = '0'
            pin_id = '0'
            return module_name, module_sub_func, group_id, pin_id

        if '_' in pin_func:
            res_dict = re.match(
                '(?P<main_name>[a-zA-Z2]+)(?P<id>(\d{1,3})?)_(?P<sub_type>[a-zA-Z]+)_?(?P<id2>(\d{1,3})?)',
                pin_func, re.IGNORECASE)
            if res_dict:
                res_dict = res_dict.groupdict()
                module_name = res_dict.get('main_name')
                module_name = self.equality_dict.get(module_name, module_name)
                module_sub_func = res_dict.get('sub_type')
                module_sub_func = self.equality_sub_dict.get(module_sub_func, module_sub_func)
                module_id = res_dict.get('id', '0')
                pin_id = res_dict.get('id2', '0')
                if module_id == '':
                    module_id = '0'
                if pin_id == '':
                    pin_id = '0'

                return module_name, module_sub_func, module_id, pin_id

        return pin_func, 'UNK', 0, 0

    def have_func(self, func_name, sub_type=None):
        for func in self.functions:
            func_, sub, _, _ = self.extract_pin_info(func)
            func_ = self.equality_dict.get(func_, func_)
            sub = self.equality_sub_dict.get(sub, sub)
            if func_name.upper() in func_.upper():
                if sub_type is not None:
                    if sub == sub_type:
                        return func
                    else:
                        return None
                return func
        else:
            return False

    def get_pair(self, func_name):
        mod_name, mod_sub, mod_id = None, None, None
        func_name = self.have_func(func_name)
        if func_name:
            mod_name, mod_sub, mod_id, pin_id = self.extract_pin_info(func_name)
        else:
            return None
        for pin in self.parent.pins[self.package]:
            pair_func_name = pin.have_func(mod_name)
            if pair_func_name:
                pair_mod_name, pair_mod_sub, pair_mod_id, pair_mod_pin_id = self.extract_pin_info(pair_func_name)
                if pair_func_name != func_name and pair_mod_id != mod_id:
                    continue
                if pin == self and pin not in self.pairs:
                    continue
                if func_name == pair_mod_name:
                    continue
                self.pairs.append(pin)
        return self.pairs

    def __repr__(self):
        return '<Pin-{} {} {}>'.format(self.pin_id, self.pin_type, '|'.join(self.functions))


class PinManager(WithParent):

    def __init__(self, pinout: Dict[str, Dict[str, Any]], requirements: Dict) -> None:
        """

        :type pinout: Dict[str, Dict[str, str]]
        """
        self.requirements = requirements  # type: Dict
        self.packages_pinout = pinout  # type: Dict[str, Dict[str, Any]]
        self.pins = {}  # type: Dict[str,List[Pin]]
        self.already_used_pins = []  # type: List[str]
        self.mcu_map = {}  # type: Dict[str, Any]
        self.failed_pins = []  # type: List[str]
        self.to_fit = []
        self.black_list = self.requirements.get('BLACK_LIST',[])

    def read_pins(self):
        for package, pinout in self.packages_pinout.items():
            self.pins[package] = []
            for pin_id, pin_data in pinout['pins'].items():
                pin = Pin(pin_id, pin_data['functions'], pin_data['type'], package)
                self.register(pin)
                self.pins[package].append(pin)

    def get_pins_by_func(self, func_name, package, sub_type=None):
        pins = []  # type: List[Pin]
        for pin in self.pins[package]:
            invalid = False
            for black_name in self.black_list:
                if pin.have_func(black_name) or pin.pin_type == 'S':
                    invalid = True
                    continue
            if pin.have_func(func_name, sub_type) and not invalid:
                pins.append(pin)
        return pins

    def resolve_conflict(self, pins: List[Pin]):
        input('GOT CONFLICT {}'.format(pins))
        # for module_name,used_pins in self.mcu_map.items():
        #     print(module_name,used_pins)

    def fit(self):
        package = self.requirements['PACKAGE']

        failed_pins = []
        if package not in self.pins.keys():
            print('THIS MCU DOES NOT HAS SUCH PACKAGE {}'.format(package))
            print('Here is available packages:')
            for pac in self.pins.keys():
                print('\t', pac)
            exit(0xDEADBEEF)
        self.to_fit = list(self.requirements['PINOUT'].items())
        for req_pin, req_pin_data in self.to_fit:

            if type(req_pin_data['PINS']) is int:
                suitable_pins = sorted(self.get_pins_by_func(req_pin_data['TYPE'], package),
                                       key=lambda pin: len(pin.functions))
                self.mcu_map[req_pin] = []
                for i in range(req_pin_data['PINS']):
                    suitable_pin = None
                    for suitable_pin in suitable_pins:
                        if suitable_pin not in self.already_used_pins:
                            self.already_used_pins.append(suitable_pin)
                            self.mcu_map[req_pin].append(suitable_pin)
                            break
                        suitable_pin = None
                    if not suitable_pin:
                        print('NO SUITABLE PINS FOR {}-{} AVAILABLE!'.format(req_pin, i))
                        self.resolve_conflict(suitable_pins)
                        failed_pins.append(req_pin)


            else:
                self.mcu_map[req_pin] = []
                if req_pin_data['TYPE'] in ['SPI', 'I2C', 'UART']:
                    suitable_pins = sorted(
                        self.get_pins_by_func(req_pin_data['TYPE'], package, req_pin_data['PINS'][0]),
                        key=lambda pin: len(pin.functions))
                    found = False
                    suitable_pin = None
                    for suitable_pin in suitable_pins:
                        if suitable_pin in self.already_used_pins:
                            continue
                        temp = {sub: False for sub in req_pin_data['PINS']}
                        if suitable_pin not in self.already_used_pins:
                            pairs = suitable_pin.get_pair(req_pin_data['TYPE'])
                            pairs.append(suitable_pin)

                            for sub_type in req_pin_data['PINS']:
                                for pair in pairs:
                                    if pair in self.already_used_pins:
                                        continue
                                    if pair.have_func(req_pin_data['TYPE'], sub_type):
                                        temp[sub_type] = pair
                                        break
                            if all(temp.values()):
                                found = True
                                for sub_name, pin in temp.items():
                                    self.already_used_pins.append(pin)
                                    self.mcu_map[req_pin].append({sub_name: pin})
                                break
                    if not found:
                        self.resolve_conflict(suitable_pins)
                        self.failed_pins.append(req_pin)





                else:
                    for sub_type in req_pin_data['PINS']:
                        suitable_pins = sorted(self.get_pins_by_func(req_pin_data['TYPE'], package, sub_type),
                                               key=lambda pin: len(pin.functions))
                        suitable_pin = None
                        for suitable_pin in suitable_pins:
                            if suitable_pin not in self.already_used_pins:
                                self.already_used_pins.append(suitable_pin)
                                self.mcu_map[req_pin].append({sub_type: suitable_pin})
                                break
                        if not suitable_pin:
                            self.resolve_conflict(suitable_pins)
                            print('NO SUITABLE PINS FOR {}-{} AVAILABLE!'.format(req_pin, sub_type))

        if not failed_pins:
            pass
            # print('MAPPED EVERYTHIGN WITHOUT ERRORS!')
        self.failed_pins = failed_pins

    def report(self):
        if self.failed_pins:
            print('Failed to find pins for this connections:')
            for pin in self.failed_pins:
                print('\t', pin)
        else:
            print('Mapped all pins without errors!')
        print('Fitted pins')
        for req_name, pin_data in self.mcu_map.items():
            print('\t', req_name, ':')
            if is_dict(pin_data):
                for pin_sub_name, pin in pin_data.items():
                    print('\t\t', pin_sub_name, ':', pin)
            else:
                for n, pin in enumerate(pin_data):
                    if type(pin) is dict:
                        item = list(pin.items())[0]
                        print('\t\t', item[0], ':', item[1])
                    else:
                        print('\t\t', n, ':', pin)

    @staticmethod
    def serialize_pin(obj):
        if type(obj) is Pin:
            return "Pin-{}".format(obj.pin_id)
        return obj

    def serialize(self,path):
        with open(path, 'w') as fp:
            json.dump(self.mcu_map, fp,default=self.serialize_pin,indent=2)

if __name__ == '__main__':
    with open('pins.json') as fp:
        pins = json.load(fp)
    with open('pins_req.json') as fp:
        req = json.load(fp)
    a = PinManager(pins, req)
    a.read_pins()
    pprint(a.fit())
    with open('fit.json') as fp:
        json.dump(a.mcu_map,fp)
    # pin = a.pins['LQFP100'][15]
    # pin = a.pins['LQFP64'][5]
    # print('The pairs of', pin, 'is', pin.get_pair('TSI'))
    # print('Pins with TSI:')
    # pprint(a.get_pins_by_func('TSI', 'LQFP64'))
    # pprint(a.pins)
