import re


def is_int(val):
    return isinstance(val, int)


def is_dict(val):
    return isinstance(val, dict)


def is_list(val):
    return isinstance(val, list)


def is_str(val):
    return isinstance(val, str)


def is_float(val):
    return isinstance(val, float)


def clean_line(line: str):
    line = line.replace('–', '-')
    line = line.replace('-', '-')
    line = line.replace('×', 'x')
    return line


def merge(source, dest):
    if is_int(source) and is_int(dest):
        return source + dest
    if is_float(source) and is_float(dest):
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


def remove_parentheses(string: str):
    if '(' in string and ')' in string:
        first = string.index('(')
        second = string.index(')', first)
        return string[:first] + string[second + 1:]
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


def text2int(textnum, numwords={}):
    if not numwords:
        units = [
            "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
            "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
            "sixteen", "seventeen", "eighteen", "nineteen",
        ]

        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

        scales = ["hundred", "thousand", "million", "billion", "trillion"]

        numwords["and"] = (1, 0)
        for idx, word in enumerate(units):  numwords[word] = (1, idx)
        for idx, word in enumerate(tens):       numwords[word] = (1, idx * 10)
        for idx, word in enumerate(scales): numwords[word] = (10 ** (idx * 3 or 2), 0)

    ordinal_words = {'first': 1, 'second': 2, 'third': 3, 'fifth': 5, 'eighth': 8, 'ninth': 9, 'twelfth': 12}
    ordinal_endings = [('ieth', 'y'), ('th', '')]
    # if '-' in textnum:
    #     negative = True
    textnum = textnum.replace('-', '- ')

    current = result = 0
    curstring = ""
    onnumber = False
    for word in textnum.split():
        if word in ordinal_words:
            scale, increment = (1, ordinal_words[word])
            current = current * scale + increment
            if scale > 100:
                result += current
                current = 0
            onnumber = True
        else:
            for ending, replacement in ordinal_endings:
                if word.endswith(ending):
                    word = "%s%s" % (word[:-len(ending)], replacement)

            if word not in numwords:
                if onnumber:
                    curstring += repr(result + current) + " "
                curstring += word + " "
                result = current = 0
                onnumber = False
            else:
                scale, increment = numwords[word]

                current = current * scale + increment
                if scale > 100:
                    result += current
                    current = 0
                onnumber = True

    if onnumber:
        curstring += repr(result + current)
    curstring = curstring.replace('- ', '-')
    return curstring


def rec_split(block, char):
    return block.split(char)


def fucking_split(block, chars):
    array = [block]
    for char in chars:
        for _ in range(len(array)):
            block = array.pop()
            array = rec_split(block, char)
    return array

def fucking_replace(string, chars,rep):
    for char in chars:
        string = string.replace(char,rep)
    return string
