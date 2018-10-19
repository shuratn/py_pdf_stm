import itertools
import json
import math
from functools import lru_cache
from pprint import pprint
from typing import List, Dict, Any, Set
import re
from random import choice, shuffle
from multiprocessing import Pool

from tqdm import tqdm

from Utils import is_dict, is_numeric, is_list, is_int, remove_doubles


class WithParent:
    parent = None

    def register(self, obj: 'WithParent'):
        obj.parent = self


class Pin(WithParent):
    equality_dict = {
        # 'LPUART': 'UART',
        'USART': 'UART',
        'TSC': 'TSI',
        'COMP': 'CMP',
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
        self.functions = set(functions)
        self.pin_type = pin_type
        self.package = package
        self.pairs = []  # type: List[Pin]
        if pin_type == 'S':
            self.functions = []

    def __hash__(self):
        return hash(self.pin_id)

    def extract_pin_info(self, pin_func: str):
        pin_func = self.equality_dict.get(pin_func, pin_func)
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
            if group_id == 'SYNC':
                return module_name, 'SYNC', 'SYNC', '-1'
            pin_id = pin_func[-1]
            return module_name, module_sub_func, group_id, pin_id
        if 'OSC' in pin_func:
            if '_' in pin_func:
                module_name, module_sub_func = pin_func.split('_', maxsplit=1)
            else:
                module_name = pin_func
                module_sub_func = 'NONE'
            group_id = None
            pin_id = '0'
            return module_name, module_sub_func, group_id, pin_id

        if '_' in pin_func:
            res_dict = re.search(
                '(?P<main_name>[a-zA-Z]+)(?P<id>(\d{1,3})?)_(?P<sub_type>[a-zA-Z]+)_?(?P<id2>(\d{1,3})?)',
                pin_func, re.IGNORECASE)
            if res_dict:
                res_dict = res_dict.groupdict()
                module_name = res_dict.get('main_name')
                if 'I2C' in pin_func:
                    module_name = 'I2C'

                module_name = self.equality_dict.get(module_name, module_name)
                module_sub_func = res_dict.get('sub_type', 'UNK')
                module_sub_func = self.equality_sub_dict.get(module_sub_func, module_sub_func)
                module_id = res_dict.get('id', '0')
                pin_id = res_dict.get('id2', '0')
                # if 'LPUART' in pin_func:
                #     module_id = str(int(module_id)+100)
                # if 'USART' in pin_func:
                #     module_id = str(int(module_id)+1000)
                if module_id == '':
                    module_id = '0'
                if pin_id == '':
                    pin_id = '0'

                return module_name, module_sub_func, module_id, pin_id

        return pin_func, 'UNK', 0, 0

    def module(self, pin_func):
        module, sub, mod_id, sub_id = self.extract_pin_info(pin_func)
        module = self.equality_dict.get(module, module)
        if mod_id:
            return '{}{}'.format(module, mod_id)
        else:
            return '{}'.format(module)
    @lru_cache(100)
    def modules_by_type(self, mod_type):
        ret = []
        for func in self.functions:
            if self.has_func(mod_type):
                mod, _, mod_id, _ = self.extract_pin_info(func)
                if mod == mod_type:
                    mod = self.module(func)
                    ret.append(mod)
        return ret

    def has_func(self, func_name, sub_type=None):
        for func in self.functions:
            func_, sub, _, _ = self.extract_pin_info(func)
            func_ = self.equality_dict.get(func_, func_)
            sub = self.equality_sub_dict.get(sub, sub)
            if func_name.upper() == func_.upper():
                if sub_type is not None:
                    if sub.upper() == sub_type.upper():
                        return func
                    else:
                        return None
                return func
        return None

    def get_pair(self, func_name):
        func_name = self.has_func(func_name)
        mod_name = self.module(func_name)
        if func_name:
            _, mod_sub, mod_id, pin_id = self.extract_pin_info(func_name)
        else:
            return None
        for pin in self.parent.pins[self.package]:
            pair_func_name = pin.has_func(mod_name)
            if pair_func_name:
                pair_mod_name = pin.module(pair_func_name)
                _, pair_mod_sub, pair_mod_id, pair_mod_pin_id = pin.extract_pin_info(pair_func_name)
                if mod_name != pair_mod_name:
                    continue
                if pin == self and pin not in self.pairs:
                    continue
                if pair_mod_name != pair_mod_name:
                    continue
                self.pairs.append(pin)
        return self.pairs

    def __repr__(self):
        return '<Pin-{} {} {}>'.format(self.pin_id, self.pin_type, ' | '.join(self.functions))

    def str_short(self):
        return '<Pin-{} {}>'.format(self.pin_id, self.pin_type)


class PinManager(WithParent):
    mergeble_types = ['I2C']

    def __init__(self, pinout: Dict[str, Dict[str, Any]], requirements: Dict) -> None:
        """

        :type pinout: Dict[str, Dict[str, str]]
        """
        self.requirements = requirements  # type: Dict
        self.packages_pinout = pinout  # type: Dict[str, Dict[str, Any]]
        self.pins = {}  # type: Dict[str,List[Pin]]
        self.useless_pins = {}  # type: Dict[str,List[Pin]]
        self.already_used_pins = set()  # type: Set[Pin]
        self.already_used_modules = set()  # type: Set[Pin]
        self.mcu_map = {}  # type: Dict[str, Any]
        self.failed_pins = []  # type: List[str]
        self.to_fit = []  # type: List
        self.black_list = set(self.requirements.get('BLACK_LIST', []))
        self.full_auto_mode = True
        self.fit_tries = 0
        self.silent_mode = True

    def read_pins(self):
        for package, pinout in self.packages_pinout.items():
            self.pins[package] = []
            self.useless_pins[package] = []
            for pin_id, pin_data in pinout['pins'].items():
                pin = Pin(pin_id, pin_data['functions'], pin_data['type'], package)
                self.register(pin)
                if pin.pin_type == 'S' or not pin.functions or set(pin.functions).intersection(set(self.black_list)):
                    self.useless_pins[package].append(pin)
                else:
                    self.pins[package].append(pin)
    @lru_cache(50)
    def get_pins_by_func(self, func_name, sub_type=None):
        package = self.requirements['PACKAGE']
        pins = filter(lambda pin: pin.has_func(func_name, sub_type), self.pins[package])
        return list(pins)

    def flatten(self, values):
        out = []
        if type(values) is list or type(values) is tuple:
            for value in values:
                out.extend(self.flatten(value))
        elif type(values) is dict:
            for name, value in values.items():
                if name == 'MODULE':
                    continue
                out.extend(self.flatten(value))
        else:
            out.append(values)
        return out

    def get_pin_user(self, to_find_pin: Pin):
        for pin_name, pins in self.mcu_map.items():
            pin_user = pin_name
            for pin in pins:
                if type(pin) is dict:
                    for pin_sub_type, pin_ in pin.items():
                        if pin_ == to_find_pin:
                            return pin_user, pin_sub_type, pin.get('MODULE')
                elif type(pin) is list:
                    for n, pin in enumerate(pin):
                        return pin_user, str(n)
                else:
                    if pin == to_find_pin:
                        return pin_user, None, 'UNK'
        return None, None, None

    def resolve_conflicts(self):
        req_pinout = self.requirements['PINOUT']
        while self.failed_pins:
            conflict = self.failed_pins.pop(0)

            req_data = req_pinout[conflict]
            req_type = req_data['TYPE']
            if self.full_auto_mode:
                if is_list(req_data['PINS']):
                    users = []
                    for sub in req_data['PINS']:
                        users.extend(
                            list(set([self.get_pin_user(pin)[0] for pin in self.get_pins_by_func(req_type, sub) if
                                      self.get_pin_user(pin)[0]])))
                    users = remove_doubles(users)
                else:
                    users = list(set([self.get_pin_user(pin)[0] for pin in self.get_pins_by_func(req_type) if
                                      self.get_pin_user(pin)[0]]))
                self.to_fit.append((conflict, req_pinout[conflict]))
                if users:
                    # shuffle(users)
                    user_to_free = list(
                        sorted(users, key=lambda user: 0 if req_pinout[user]['TYPE'] == 'GPIO' else 10000))

                    # user_to_free = choice(users)
                    if not self.silent_mode:
                        print('Decided to re-fit', user_to_free)

                    for user_to_free in users:
                        user_pin_type = req_pinout[user_to_free]['TYPE']
                        self.to_fit.append((user_to_free, req_pinout[user_to_free]))

                        for pins in self.mcu_map[user_to_free]:
                            if is_dict(pins):
                                module = pins['MODULE']
                                pins = self.flatten(pins)
                                if module in self.already_used_modules:
                                    self.already_used_modules.remove(module)
                                for pin in pins:
                                    self.already_used_pins.remove(pin)
                            elif user_pin_type == 'GPIO':
                                if user_pin_type in self.already_used_modules:
                                    self.already_used_modules.remove(user_pin_type)
                                self.already_used_pins.remove(pins)
                            else:
                                raise NotImplementedError
                        del self.mcu_map[user_to_free]

                        # shuffle(self.to_fit)
                        # self.fit(False)
                shuffle(self.to_fit)

                # self.fit()
            else:
                print('GOT CONFLICT {}'.format(conflict))
                print('List of required pins:')
                if type(req_data['PINS']) is list:
                    for req_pin in req_data['PINS']:
                        print('{}-{}'.format(req_type, req_pin))
                else:
                    for req_pin in range(req_data['PINS']):
                        print('{}-{}'.format(req_type, req_pin))
                pins = self.get_pins_by_func(req_type)
                print('Suitable pins:')
                for pin in pins:
                    user, sub_type, mod = self.get_pin_user(pin)
                    if user:
                        print('\t', pin, '{} used by - {}-{}'.format(mod, user, sub_type))
                    else:
                        print('\t', pin, 'is free')
                print('You can:\n1. Free pins and re-fit them again\n2. Skip this conflict')
                type_of_resolve = input('What do you choose?')
                if not is_numeric(type_of_resolve):
                    print('Please use numbers!')
                    type_of_resolve = input('What do you choose?')
                    if not is_numeric(type_of_resolve):
                        print('Screew you, I\'m going home!')
                        self.failed_pins.append(conflict)
                type_of_resolve = int(type_of_resolve)
                if type_of_resolve == 1:

                    print('What pins do you want to set free?')
                    i_want_them_free = input(
                        'Please specify what they are used BY, not their ID. Separate them with ; : ')
                    i_want_them_free = i_want_them_free.split(';')
                    for free in i_want_them_free:
                        if free in req_pinout:
                            for pins in self.mcu_map[free]:
                                if is_dict(pins):
                                    module = pins.get('MODULE')
                                    if module in self.already_used_modules:
                                        self.already_used_modules.remove(module)
                                pins = self.flatten(pins)

                                for pin in pins:
                                    temp = list(set(self.already_used_pins))
                                    self.already_used_pins = temp
                                    if pin not in self.already_used_pins:
                                        continue
                                    self.already_used_pins.remove(pin)
                            del self.mcu_map[free]
                            self.to_fit.append((free, req_pinout[free]))
                        else:
                            print('Invalid user {}'.format(free))
                    self.to_fit.append((conflict, req_pinout[conflict]))
                    # self.fit()
                elif type_of_resolve == 2:
                    self.to_fit.append((conflict, req_pinout[conflict]))
                    # self.failed_pins.append(conflict)
            # if self.to_fit:
            #     self.fit()

    def fit_pins(self):
        package = self.requirements['PACKAGE']
        if package not in self.pins.keys():
            print('THIS MCU DOES NOT HAS SUCH PACKAGE {}'.format(package))
            print('Here is available packages:')
            for pac in self.pins.keys():
                print('\t', pac)
            exit(0xDEADBEEF)
        self.count_modules()
        all_pins = list(self.requirements['PINOUT'].items())[::-1]
        filthy_gpios = [pin for pin in all_pins if pin[1]['TYPE'] == 'GPIO']
        everything_else = [pin for pin in all_pins if pin[1]['TYPE'] != 'GPIO']
        self.to_fit = everything_else
        # shuffle(self.to_fit)
        self.fit_tries += 1
        all_possible_variants = itertools.permutations(everything_else)
        for variant in tqdm(all_possible_variants, desc='Trying all possible variants!', unit='variant',
                            total=math.factorial(len(everything_else))):
            self.failed_pins.clear()
            self.already_used_modules.clear()
            self.already_used_pins.clear()
            self.to_fit = list(variant)
            self.fit(False)
            if not any(self.failed_pins):
                break
        if any(self.to_fit):
            raise Exception('Some pins were not fitted during first stage\nThat\'s means something went wrong!')
        self.to_fit.extend(filthy_gpios)
        self.fit(True)

    def check_module(self, pin, mod_name):
        valid = False
        if mod_name == 'GPIO':
            return True
        for mod in pin.modules_by_type(mod_name):
            if mod not in self.already_used_modules:
                valid = True
                # self.already_used_modules.append(mod)
                break
        return valid
    def get_free_modules(self, modules):
        ret = []
        for mod in modules:
            if mod not in self.already_used_modules or mod == 'GPIO':
                ret.append(mod)
        return ret

    def count_modules(self):
        mcu_modules = {}
        already_checked = []
        have_issues = False
        package = self.requirements['PACKAGE']
        for pin in self.pins[package]:
            for func in pin.functions:
                module, _, _, _ = pin.extract_pin_info(func)
                module_with_id = pin.module(func)
                if module_with_id not in already_checked or module_with_id == 'GPIO':
                    already_checked.append(module_with_id)
                    if mcu_modules.get(module, False):
                        mcu_modules[module] += 1
                    else:
                        mcu_modules[module] = 1

        # print(mcu_modules)
        req_modules = {}
        for req_name, req_data in self.requirements['PINOUT'].items():
            req_type = req_data['TYPE']
            if req_modules.get(req_type, False):
                req_modules[req_type] += 1
            else:
                req_modules[req_type] = 1
        # print(mcu_modules)
        # print(req_modules)
        for req_module, req_module_count in req_modules.items():
            if req_module not in mcu_modules:
                print('MISSING MODULE {}'.format(req_module))
                have_issues = True
                continue
            if mcu_modules[req_module] < req_module_count:
                have_issues = True
                print('INSUFFICIENT MODULE COUNT {}, REQUIRED {} HAVE {}'.format(req_module, req_module_count,
                                                                                 mcu_modules[req_module]))
        if have_issues:
            print('Solve issues printed above and come again later')
            exit(1)

    def fit(self, handle_conflicts=True):
        # for req_pin, req_pin_data in self.to_fit:
        package = self.requirements['PACKAGE']
        all_pins = set(self.pins[package])
        while self.to_fit:
            req_pin, req_pin_data = self.to_fit.pop(-1)
            self.mcu_map[req_pin] = []
            req_type = req_pin_data['TYPE']
            req_sub_types = req_pin_data['PINS']
            found = False
            any_free_pins = all_pins.difference(self.already_used_pins)
            if not any(any_free_pins):
                raise Exception('No free pins left!')
            if is_int(req_sub_types):
                for i in range(req_sub_types):
                    suitable_pins = sorted(self.get_pins_by_func(req_type),
                                                       key=lambda pin: len(pin.functions))
                    suitable_pins = set(suitable_pins).intersection(any_free_pins)
                    for suitable_pin in suitable_pins:
                        if self.check_module(suitable_pin, req_type):
                            mod = self.get_free_modules(suitable_pin.modules_by_type(req_type))[0]
                            self.already_used_pins.add(suitable_pin)
                            self.already_used_modules.add(mod)
                            self.mcu_map[req_pin].append(suitable_pin)
                            found = True
                            break
                    else:
                        raise Exception('No free pins left! Can\'t fit {}-{}'.format(req_pin, i + 1))
                    if not found:
                        if not self.silent_mode:
                            print('NO SUITABLE PINS FOR {}-{} AVAILABLE!'.format(req_pin, i + 1))
                        self.failed_pins.append(req_pin)
                        return

            else:
                if req_type in ['SPI', 'I2C', 'UART', 'TSC', 'TSI', 'OSC', 'CMP', 'OSC32']:
                    suitable_pins = filter(lambda pin: pin not in self.already_used_pins,
                                           self.get_pins_by_func(req_type, req_sub_types[0]))
                    for suitable_pin in suitable_pins:
                        if self.check_module(suitable_pin, req_type):
                            mod = self.get_free_modules(suitable_pin.modules_by_type(req_type))[0]
                            temp = [(req_sub_types[0], suitable_pin, mod)]
                            local_used_pins = [suitable_pin]
                            for sub_type in req_sub_types[1:]:
                                pairs = filter(lambda pin: pin not in self.already_used_pins,
                                               self.get_pins_by_func(req_type, sub_type))
                                for pair in pairs:
                                    if pair in local_used_pins:
                                        continue
                                    pair_mod = self.get_free_modules(pair.modules_by_type(req_type))
                                    if not pair_mod:
                                        break
                                    pair_mod = pair_mod[0]
                                    if mod != pair_mod:
                                        continue
                                    local_used_pins.append(pair)
                                    temp.append((sub_type, pair, pair_mod))
                                    break
                            if len(temp) == len(req_sub_types):
                                found = True
                                for sub_name, pin, mod in temp:
                                    self.already_used_pins.add(pin)
                                    self.already_used_modules.add(mod)
                                    self.mcu_map[req_pin].append({sub_name: pin, 'MODULE': mod})
                                break
                    if not found:
                        if not self.silent_mode:
                            print('NO SUITABLE PINS FOR {} AVAILABLE!'.format(req_pin))
                        self.failed_pins.append(req_pin)
                        return

                else:
                    raise NotImplementedError()
            # self.failed_pins = remove_doubles(self.failed_pins)
            if any(self.failed_pins):
                return
            # if any(self.failed_pins) and handle_conflicts:
            #     # self.fit_tries += 1
            #     pass
            #     self.resolve_conflicts()

    def report(self):
        if self.failed_pins:
            print('Failed to find pins for this connections:')
            for pin in self.failed_pins:
                print('\t', pin)
        else:
            print('Mapped all pins without errors in {} tries!'.format(self.fit_tries))
        print('Fitted pins')
        package = self.requirements['PACKAGE']
        for req_name, pin_data in self.mcu_map.items():
            req_data = self.requirements['PINOUT'][req_name]
            req_type = req_data['TYPE']
            print('\t', req_name, ':')
            for pins in pin_data:
                if is_list(pins):
                    for pin in pins:
                        print('\t\t', req_type, ':', pin)
                elif is_dict(pins):

                    print('\t\t', pins.pop('MODULE'), ':', list(pins.values())[0])
                else:
                    print('\t\t', req_type, ':', pins)

        free_pins = set(self.pins[package]).difference(set(self.already_used_pins))
        if free_pins:
            print('List of free and usable pins')
            for pin in free_pins:
                print('\t', pin)

    @staticmethod
    def serialize_pin(obj):
        if type(obj) is Pin:
            return "Pin-{}".format(obj.pin_id)
        return obj

    def serialize(self, path):
        with open(path, 'w') as fp:
            json.dump(self.mcu_map, fp, default=self.serialize_pin, indent=2)


if __name__ == '__main__':
    with open('pins.json') as fp:
        pins = json.load(fp)
    with open('pins_req.json') as fp:
        req = json.load(fp)
    a = PinManager(pins, req)
    a.read_pins()
    pprint(a.fit())
    with open('fit.json') as fp:
        json.dump(a.mcu_map, fp)
    # pin = a.pins['LQFP100'][15]
    # pin = a.pins['LQFP64'][5]
    # print('The pairs of', pin, 'is', pin.get_pair('TSI'))
    # print('Pins with TSI:')
    # pprint(a.get_pins_by_func('TSI', 'LQFP64'))
    # pprint(a.pins)
