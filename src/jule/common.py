import logging
from typing import List, Dict

LOGGER = logging.getLogger(__name__)


def decode_text(value: bytes):
    return value.decode('utf8')


def decode_single_text(value: List[bytes]):
    if len(value) > 1:
        LOGGER.warning('unexpectedly more than value for attribute: "%s"', value)
    return decode_text(value[0])


def load_text_attr(entry: Dict, attr_name: str):
    if attr_name not in entry:
        return None
    return decode_single_text(entry[attr_name])


def split_dn(dn: str):
    components = []
    buffer = ''
    idx = 0
    n = len(dn)

    while True:
        if idx >= n:
            break
        if dn[idx] == ',':
            components.append(buffer)
            buffer = ''
        else:
            buffer += dn[idx]
            if dn[idx] == '\\':
                idx += 1
                buffer += dn[idx]
        idx += 1

    if buffer:
        components.append(buffer)

    return components


def fully_qualified_class_name(klass):
    module = klass.__module__
    if module == 'builtins':
        return klass.__qualname__
    return module + '.' + klass.__qualname__
