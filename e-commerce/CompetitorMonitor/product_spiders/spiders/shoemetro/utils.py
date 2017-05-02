__author__ = 'juraseg'

import re

regexs = [
    re.compile(r'(?P<name>.*) (?P<color>[^\s]+) Size - (?P<size>[\d.-]+( Months)?)$'),
    re.compile(r'(?P<name>.*)\s+Size - (?P<size>[\d.]+) \((?P<color>.*)\)$')
]

def parse_shoemetro_result_name(name):
    for r in regexs:
        m = re.search(r, name)
        if m:
            break
    else:
        return None

    name = m.group('name').lower()
    color = m.group('color').lower()
    size = m.group('size').lower()

    return name, color, size