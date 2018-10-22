import itertools
import json
import math
import multiprocessing
import struct
from multiprocessing.pool import ThreadPool
from multiprocessing import Pool
from functools import lru_cache
from pprint import pprint
from typing import List, Dict, Any, Set, Tuple
import re

from tqdm import tqdm

from Utils import is_dict, is_numeric, is_list, is_int, remove_doubles


class Pin:
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

    def __init__(self, pin_id: str, functions: List[str], pin_type: str, package: str) -> None:
        """
        :type pin_type: str IO or S
        :type functions: List[str] Array of pin functions
        :type pin_id: str Name\Id of pin
        """
        self.pin_id = pin_id
        self.used_module = 'GPIO'
        self.functions = set(functions)
        self.pin_type = pin_type
        self.package = package
        self.pairs = []  # type: List[Pin]
        if pin_type == 'S':
            self.functions = []

    def __eq__(self, other:'Pin'):
        return self.pin_id == other.pin_id
    def __hash__(self):
        return hash(self.pin_id)

    @lru_cache(200)
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

    @lru_cache(200)
    def modules_by_type(self, mod_type) -> Set:
        ret = set()
        for func in self.functions:
            if self.has_func(mod_type):
                mod, _, mod_id, _ = self.extract_pin_info(func)
                if mod == mod_type:
                    mod = self.module(func)
                    ret.add(mod)
        return ret

    @lru_cache(200)
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

    def __repr__(self):
        return '<Pin-{} {} {}>'.format(self.pin_id, self.pin_type, ' | '.join(self.functions))

    def str_short(self):
        return '<Pin-{} {} {}>'.format(self.pin_id, self.pin_type, self.used_module)


class PinManager:
    mergeble_types = ['I2C']

    def __init__(self, pinout: Dict[str, Dict[str, Any]], requirements: Dict) -> None:
        """

        :type pinout: Dict[str, Dict[str, str]]
        """
        self.requirements = requirements  # type: Dict
        self.packages_pinout = pinout  # type: Dict[str, Dict[str, Any]]
        self.pins = set()  # type: Set[Pin]
        self.packages = []  # type: List[str]
        self.useless_pins = {}  # type: Dict[str,List[Pin]]
        self.already_used_pins = set()  # type: Set[Pin]
        self.already_used_modules = set()  # type: Set[str]
        self.mcu_map = {}  # type: Dict[str, Any]
        self.failed_pins = []  # type: List[str]
        self.to_fit = []  # type: List
        self.black_list = set(self.requirements.get('BLACK_LIST', []))
        self.package = self.requirements.get('PACKAGE', 'You forgot to fill requirements!')
        self.full_auto_mode = True
        self.fit_variants = 0
        self.silent_mode = True

    def read_pins(self):
        for package, pinout in self.packages_pinout.items():
            self.packages.append(package)
            self.useless_pins[package] = []
            if package == self.package:
                for pin_id, pin_data in pinout['pins'].items():
                    pin = Pin(pin_id, pin_data['functions'], pin_data['type'], package)
                    if pin.pin_type == 'S' or not pin.functions or set(pin.functions).intersection(self.black_list):
                        self.useless_pins[package].append(pin)
                    else:
                        self.pins.add(pin)

    @lru_cache(500)
    def get_pins_by_func(self, func_name, sub_type=None) -> Set[Pin]:
        pins = filter(lambda pin: pin.has_func(func_name, sub_type), self.pins)
        return set(pins)

    def fit_pins(self):
        if self.package not in self.packages:
            print('THIS MCU DOES NOT HAS SUCH PACKAGE {}'.format(self.package))
            print('Here is available packages:')
            for pac in self.packages:
                print('\t', pac)
            exit(0xDEADBEEF)
        self.count_modules()
        all_pins = list(self.requirements['PINOUT'].items())
        filthy_gpios = [pin for pin in all_pins if pin[1]['TYPE'] == 'GPIO']
        everything_else = [pin for pin in all_pins if pin[1]['TYPE'] != 'GPIO']
        self.to_fit = everything_else

        all_possible_variants = itertools.permutations(everything_else)
        with Pool(processes=10) as pool:
            with tqdm(all_possible_variants, desc='Trying all possible variants!', unit=' variant',
                      total=math.factorial(len(everything_else))) as pb:
                for result in pool.imap_unordered(self.fit,pb,chunksize=10000):
                    new_map, fails, used_pins = result
                    if new_map:
                        self.already_used_pins = set(list(used_pins))
                        self.mcu_map.update(new_map)
                        self.fit_variants += 1
                        if not (self.fit_variants % 100):
                            pb.set_description('Found {} working variants'.format(self.fit_variants))
                        # pass
                        break
                        # print('FOUND')
                    #     break
                pb.set_description('Found {} working variants'.format(self.fit_variants))
                pb.close()
        # self.to_fit.extend(filthy_gpios)
        new_map, _, gpio_used_pins = self.fit(filthy_gpios, already_used_pins=self.already_used_pins,
                                              gpio=True)
        self.mcu_map.update(new_map)
        self.already_used_pins |= gpio_used_pins


    @staticmethod
    def get_free_modules(modules: Set[str], already_used_modules) -> Set[str]:
        return modules.difference(already_used_modules)

    def count_modules(self):
        mcu_modules = {}
        already_checked = []
        have_issues = False
        for pin in self.pins:
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

    def fit(self, to_fit, already_used_pins=None,gpio = False) -> Tuple[Dict[str,Any], Any, Any]:
        if already_used_pins is None:
            already_used_pins = set()
        else:
            already_used_pins = set(list(already_used_pins))
        mcu_map = {}
        already_used_modules = set()
        failed_pins = []
        to_fit = list(to_fit)
        while to_fit:
            req_pin, req_pin_data = to_fit.pop(-1)
            mcu_map[req_pin] = []
            req_type = req_pin_data['TYPE']
            req_sub_types = req_pin_data['PINS']
            found = False
            if len(already_used_pins) >= len(self.pins):
                raise Exception('No free pins left!')
            if is_list(req_sub_types):
                suitable_pins = self.get_pins_by_func(req_type, req_sub_types[0]).difference(already_used_pins)
                for suitable_pin in suitable_pins:
                    mod = self.get_free_modules(suitable_pin.modules_by_type(req_type), already_used_pins)
                    if mod:
                        mod = mod.pop()
                        temp = [(req_sub_types[0], suitable_pin, mod)]
                        local_used_pins = [suitable_pin]
                        for sub_type in req_sub_types[1:]:
                            pairs = self.get_pins_by_func(req_type, sub_type) \
                                .difference(already_used_pins) \
                                .difference(local_used_pins)
                            for pair in pairs:
                                pair_mod = self.get_free_modules(pair.modules_by_type(req_type), already_used_pins)
                                if pair_mod:
                                    pair_mod = pair_mod.pop()
                                    if mod != pair_mod:
                                        continue
                                    local_used_pins.append(pair)
                                    temp.append((sub_type, pair, pair_mod))
                                    break
                        if len(temp) == len(req_sub_types):
                            found = True
                            for sub_name, pin, mod in temp:
                                already_used_pins.add(pin)
                                already_used_modules.add(mod)
                                mcu_map[req_pin].append({sub_name: pin, 'MODULE': mod})
                            break
                    if found:
                        break
                if not found:
                    if not self.silent_mode:
                        print('NO SUITABLE PINS FOR {} AVAILABLE!'.format(req_pin))
                    failed_pins.append(req_pin)
                    return {}, failed_pins, None

            else:
                for i in range(req_sub_types):
                    suitable_pins = set(sorted(self.get_pins_by_func(req_type),
                                           key=lambda pin: len(pin.functions)))
                    avalible_pins = suitable_pins.difference(already_used_pins)
                    for suitable_pin in avalible_pins:
                        mod = set(suitable_pin.modules_by_type(req_type)).difference(already_used_modules)
                        if mod:
                            mod = mod.pop()
                            already_used_pins.add(suitable_pin)
                            if mod != 'GPIO':
                                already_used_modules.add(mod)
                            mcu_map[req_pin].append(suitable_pin)
                            found = True
                            break
                    else:
                        raise Exception('No free pins left! Can\'t fit {}-{}'.format(req_pin, i + 1))
                    if not found:
                        if not self.silent_mode:
                            print('NO SUITABLE PINS FOR {}-{} AVAILABLE!'.format(req_pin, i + 1))
                        failed_pins.append(req_pin)
                        return {}, failed_pins, None

        if any(failed_pins):
            return {}, failed_pins, None
        else:
            return mcu_map, failed_pins, already_used_pins

    def report(self):
        if self.failed_pins:
            print('Failed to find pins for this connections:')
            for pin in self.failed_pins:
                print('\t', pin)
        else:
            print('Mapped all pins without errors!')
            print('Found {} working variants'.format(self.fit_variants))
        print('Fitted pins')
        for req_name, pin_data in self.mcu_map.items():
            req_data = self.requirements['PINOUT'][req_name]
            req_type = req_data['TYPE']
            print('\t', req_name, ':')
            for n, pins in enumerate(pin_data):
                if is_list(pins):
                    for pin in pins:
                        print('\t\t', req_type, ':', pin)
                elif is_dict(pins):

                    pin = list(pins.values())[0]  # type: Pin
                    pin.used_module = '{}-{}'.format(pins['MODULE'], req_data['PINS'][n])
                    print('\t\t', pin.used_module, ':', pin)
                else:
                    print('\t\t', req_type, ':', pins)

        free_pins = self.pins.difference(self.already_used_pins)
        if free_pins:
            print('List of free and usable pins')
            for pin in free_pins:
                print('\t', pin)

    @staticmethod
    def serialize_pin(obj):
        if type(obj) is Pin:
            return obj.str_short()
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

    # pin = a.pins['LQFP100'][15]
    # pin = a.pins['LQFP64'][5]
    # print('The pairs of', pin, 'is', pin.get_pair('TSI'))
    # print('Pins with TSI:')
    # pprint(a.get_pins_by_func('TSI', 'LQFP64'))
    # pprint(a.pins)
