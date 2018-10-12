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
            new_block = array.pop(0)
            array2 = rec_split(new_block, char)
            array.extend(array2)
    return array


def fucking_replace(string, chars, rep):
    for char in chars:
        string = string.replace(char, rep)
    return string


def latin1_to_ascii(unicrap):
    """This takes a UNICODE string and replaces Latin-1 characters with
        something equivalent in 7-bit ASCII. It returns a plain ASCII string.
        This function makes a best effort to convert Latin-1 characters into
        ASCII equivalents. It does not just strip out the Latin-1 characters.
        All characters in the standard 7-bit ASCII range are preserved.
        In the 8th bit range all the Latin-1 accented letters are converted
        to unaccented equivalents. Most symbol characters are converted to
        something meaningful. Anything not converted is deleted.
    """
    xlate = {0xc0: 'A', 0xc1: 'A', 0xc2: 'A', 0xc3: 'A', 0xc4: 'A', 0xc5: 'A',
             0xc6: 'Ae', 0xc7: 'C',
             0xc8: 'E', 0xc9: 'E', 0xca: 'E', 0xcb: 'E',
             0xcc: 'I', 0xcd: 'I', 0xce: 'I', 0xcf: 'I',
             0xd0: 'Th', 0xd1: 'N',
             0xd2: 'O', 0xd3: 'O', 0xd4: 'O', 0xd5: 'O', 0xd6: 'O', 0xd8: 'O',
             0xd9: 'U', 0xda: 'U', 0xdb: 'U', 0xdc: 'U',
             0xdd: 'Y', 0xde: 'th', 0xdf: 'ss',
             0xe0: 'a', 0xe1: 'a', 0xe2: 'a', 0xe3: 'a', 0xe4: 'a', 0xe5: 'a',
             0xe6: 'ae', 0xe7: 'c',
             0xe8: 'e', 0xe9: 'e', 0xea: 'e', 0xeb: 'e',
             0xec: 'i', 0xed: 'i', 0xee: 'i', 0xef: 'i',
             0xf0: 'th', 0xf1: 'n',
             0xf2: 'o', 0xf3: 'o', 0xf4: 'o', 0xf5: 'o', 0xf6: 'o', 0xf8: 'o',
             0xf9: 'u', 0xfa: 'u', 0xfb: 'u', 0xfc: 'u',
             0xfd: 'y', 0xfe: 'th', 0xff: 'y',
             0xa1: '!', 0xa2: '{cent}', 0xa3: '{pound}', 0xa4: '{currency}',
             0xa5: '{yen}', 0xa6: '|', 0xa7: '{section}', 0xa8: '{umlaut}',
             0xa9: '{C}', 0xaa: '{^a}', 0xab: '<<', 0xac: '{not}',
             0xad: '-', 0xae: '{R}', 0xaf: '_', 0xb0: '{degrees}',
             0xb1: '{+/-}', 0xb2: '{^2}', 0xb3: '{^3}', 0xb4: "'",
             0xb5: '{micro}', 0xb6: '{paragraph}', 0xb7: '*', 0xb8: '{cedilla}',
             0xb9: '{^1}', 0xba: '{^o}', 0xbb: '>>',
             0xbc: '{1/4}', 0xbd: '{1/2}', 0xbe: '{3/4}', 0xbf: '?',
             0xd7: '*', 0xf7: '/'
             }

    r = ''
    for i in unicrap:
        if ord(i) in xlate:
            r += xlate[ord(i)]
        # elif ord(i) >= 0x80:
        #     pass
        else:
            r += str(i)
    return r
