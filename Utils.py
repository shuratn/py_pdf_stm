import re


def is_int(val):
    return isinstance(val, int)


def is_dict(val):
    return isinstance(val, dict)


def is_list(val):
    return isinstance(val, list)


def is_str(val):
    return isinstance(val, str)


def merge(source, dest):
    if is_int(source) and is_int(dest):
        return source + dest
    if is_str(source) and is_str(dest):
        return dest + '/' + source
    if is_list(source) and is_list(dest):
        return list(set(dest + source))
    if source is None or dest is None:
        return source or dest

    if is_dict(source) and is_dict(dest):
        for key in set(source) | set(dest):
            dest[key] = merge(source.get(key), dest.get(key))
        return dest


def fetch_from_all(lists, num):
    return [arr[num] for arr in lists]


def remove_parentheses(string:str):
    if '(' in string and ')' in string:
        first = string.index('(')
        second = string.index(')',first)
        return string[:first]+string[second+1:]
    return string

def replace_i(string: str, sub: str, new: str):
    result = re.search('{}'.format(sub.lower()), string, re.IGNORECASE)
    string = string[:result.start()] + new + string[result.end():]
    string = string.strip(' ')
    return string


def remove_units(string: str, unit: str):
    if '(' in string:
        string = replace_i(string, '{}'.format(unit), '')
        string = string.replace('()', '')
    else:
        string = replace_i(string, '{}'.format(unit), '')
    string = string.strip()
    return string

def is_numeric(value):
    return type(value) == str and value.isnumeric()