#! /usr/bin/env python3
import abc
import argparse
import csv
import fnmatch
import json
import logging
import re
import sys
from typing import List, Dict, Optional

import coloredlogs
import pandas
import pandasql
import tabulate

from jule.common import (
    Extractor,
    Property,
)
from jule.state import LdapStorageContainer, LdapSnapshotData

LOGGER = logging.getLogger(__name__)


class BaseFormatter:
    def format(self, data: List[Dict]):
        LOGGER.debug('formatting %d entries...', len(data))
        self.format_impl(data)

    @abc.abstractmethod
    def format_impl(self, data: List[Dict]):
        raise NotImplementedError


class TableFormatter(BaseFormatter):
    def format_impl(self, data: List[Dict]):
        print(tabulate.tabulate(data, headers='keys', tablefmt='simple'))


class CsvFormatter(BaseFormatter):
    def format_impl(self, data: List[Dict]):
        if not data:
            return
        field_names = list(data[0].keys())
        writer = csv.DictWriter(sys.stdout, fieldnames=field_names, delimiter=',')
        writer.writeheader()
        for item in data:
            writer.writerow(item)


class JsonlFormatter(BaseFormatter):
    def format_impl(self, data: List[Dict]):
        for item in data:
            print(json.dumps(item))


class JsonFormatter(BaseFormatter):
    def format_impl(self, data: List[Dict]):
        json.dump(data, fp=sys.stdout)


FORMATS = {
    'table': TableFormatter(),
    'csv': CsvFormatter(),
    'json': JsonFormatter(),
    'jsonl': JsonlFormatter(),
}


def query_list(snapshot: LdapSnapshotData, properties: Optional[List[str]] = None):
    properties = properties or [
        Property.FULL_NAME, Property.TITLE, Property.DEPARTMENT,
        Property.MANAGER_NAME
    ]
    extractor = Extractor(snapshot)

    items = []
    for entry_dn in sorted(extractor.entry_by_dn.keys()):
        items.append({
            prop: extractor.extract(entry_dn, prop)
            for prop in properties
        })
    return items


def query_pandas(snapshot: LdapSnapshotData, query: str):
    extractor = Extractor(snapshot)
    data = []
    for entry_dn in extractor.entry_by_dn:
        row = dict({
            str(prop): extractor.extract(entry_dn, prop)
            for prop in Property
        }, dn=entry_dn)
        data.append(row)

    df = pandas.DataFrame.from_records(data)
    result_df = pandasql.sqldf(query, {
        'entries': df,
    })

    return result_df.to_dict('records')


def is_glob_match(pattern: str, string: str):
    string = string or ''
    regex = fnmatch.translate(pattern)
    return re.fullmatch(regex, string, flags=re.IGNORECASE)


# TODO: this module is extremely dependent on specific layout
#  may be it should be dropped altogether

def query_subordinate_tree(
        snapshot: LdapSnapshotData, name_pattern: str,
        max_distance: Optional[int], min_distance: Optional[int],
        properties: Optional[List[str]] = None):

    properties = properties or [
        Property.FULL_NAME, Property.TITLE, Property.DEPARTMENT,
        Property.MANAGER_NAME
    ]

    extractor = Extractor(snapshot)

    subordinates = []

    # this is not cycle proof
    def traverse(entry_dn, distance):

        # distance cut-off
        if max_distance is not None and distance > max_distance:
            return

        subordinates.append((entry_dn, distance))
        for subordinate_dn in extractor.manager_dn_to_subordinate_dns.get(entry_dn, []):
            traverse(subordinate_dn, distance + 1)

    # add seed entries
    for entry_dn, entry in snapshot.entries:
        full_name = extractor.extract(entry_dn, Property.FULL_NAME)
        if is_glob_match(name_pattern, full_name):
            traverse(entry_dn, 0)

    items = []
    for entry_dn, distance in sorted(subordinates, key=lambda t: (t[1], t[0])):
        if min_distance is not None and distance < min_distance:
            continue
        items.append(dict(distance=distance, **{
            prop: extractor.extract(entry_dn, prop)
            for prop in properties
        }))
    return items


def query_root_path(
        snapshot: LdapSnapshotData, name_pattern: str,
        properties: Optional[List[str]] = None):
    properties = properties or [
        Property.FULL_NAME, Property.TITLE, Property.DEPARTMENT,
        Property.MANAGER_NAME
    ]
    extractor = Extractor(snapshot)
    result = []

    def traverse(entry_dn, distance):
        result.append((entry_dn, distance))
        manager_dn = extractor.extract(entry_dn, Property.MANAGER_DN)
        if manager_dn in extractor.entry_by_dn:
            traverse(manager_dn, distance + 1)

    for entry_dn, entry in snapshot.entries:
        full_name = extractor.extract(entry_dn, Property.FULL_NAME)
        if is_glob_match(name_pattern, full_name):
            traverse(entry_dn, 0)

    items = []
    for entry_dn, distance in sorted(result, key=lambda t: (t[1], t[0])):
        items.append(dict(distance=distance, **{
            prop: extractor.extract(entry_dn, prop)
            for prop in properties
        }))
    return items


def diff(
        current: LdapSnapshotData, baseline: LdapSnapshotData,
        properties: Optional[List[str]] = None):
    properties = properties or [Property.DN, Property.DEPARTMENT, Property.TITLE]
    current_extractor = Extractor(current)
    baseline_extractor = Extractor(baseline)

    items = []
    for entry_dn in current_extractor.entry_by_dn:
        if entry_dn not in baseline_extractor.entry_by_dn:
            items.append(dict(diff='added', **{
                prop: current_extractor.extract(entry_dn, prop)
                for prop in properties
            }))

    for entry_dn in baseline_extractor.entry_by_dn:
        if entry_dn not in current_extractor.entry_by_dn:
            items.append(dict(diff='removed', **{
                prop: baseline_extractor.extract(entry_dn, prop)
                for prop in properties
            }))
    return items


def order_by(data: List[Dict], properties: List[str]):

    # this wrapper allows to handle for None case as None is not directly
    # comparable with strings
    class Wrapper:
        __slots__ = ['val']

        NULL_VALUES = {
            str: '',
            int: 0,
        }
        LOGGER = logging.getLogger('comparator')

        def __init__(self, val):
            self.val = val

        def __lt__(self, other):
            assert isinstance(other, Wrapper)
            if self.val is not None and other.val is not None:
                return self.val < other.val
            if self.val is None and other.val is None:
                return False
            assert self.val is None or other.val is None
            if self.val is not None:
                t = type(self.val)
            else:
                t = type(other.val)
            if t in self.NULL_VALUES:
                self_val = self.val if self.val is not None else self.NULL_VALUES[t]
                other_val = other.val if other.val is not None else self.NULL_VALUES[t]
            else:
                self.LOGGER.warning('unsupported type: %s', t)
                self_val = str(self.val)
                other_val = str(other.val)
            return self_val < other_val

    def resolve(item, prop):
        if prop not in item:
            raise Exception('Available keys: %s' % ', '.join(item.keys()))
        return item[prop]

    def get_sort_key(item):
        return tuple(Wrapper(resolve(item, prop)) for prop in properties)

    return sorted(data, key=get_sort_key)


def load_snapshot(path: str) -> LdapStorageContainer:
    LOGGER.info('loading "%s"...', path)
    with open(path, 'rb') as f:
        container = LdapStorageContainer.load(f)
        LOGGER.info('loaded %d entries', len(container.data.entries))
        return container


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('path', type=str)

    subparsers = parser.add_subparsers()

    def add_format_argument(parser_):
        parser_.add_argument('--format', type=str, required=False, choices=FORMATS.keys())

    def add_select_argument(parser_):
        choices = ['*'] + [str(prop.value) for prop in Property]
        parser_.add_argument('--select', nargs='+', metavar='PROPERTY', choices=choices)

    def add_order_by_argument(parser_):
        parser_.add_argument('--order-by', nargs='+', metavar='FIELD')

    list_parser = subparsers.add_parser('list')
    list_parser.set_defaults(action='list')
    list_parser.add_argument('--select', nargs='+', metavar='PROPERTY')
    add_format_argument(list_parser)
    add_order_by_argument(list_parser)

    pandasql_parser = subparsers.add_parser('pandasql')
    pandasql_parser.set_defaults(action='pandasql')
    pandasql_parser.add_argument('--query', type=str, required=True)
    add_format_argument(pandasql_parser)

    subordinates_parser = subparsers.add_parser('subordinates')
    subordinates_parser.set_defaults(action='subordinates')
    subordinates_parser.add_argument('pattern', type=str)
    subordinates_parser.add_argument('--max-distance', type=int, default=None, required=False)
    subordinates_parser.add_argument('--min-distance', type=int, default=None, required=False)
    add_select_argument(subordinates_parser)
    add_format_argument(subordinates_parser)
    add_order_by_argument(subordinates_parser)

    root_path_parser = subparsers.add_parser('root-path')
    root_path_parser.set_defaults(action='root-path')
    root_path_parser.add_argument('pattern', type=str)
    add_select_argument(root_path_parser)
    add_format_argument(root_path_parser)
    add_order_by_argument(root_path_parser)

    diff_parser = subparsers.add_parser('diff')
    diff_parser.set_defaults(action='diff')
    diff_parser.add_argument('baseline_path', type=str)
    add_select_argument(diff_parser)
    add_format_argument(diff_parser)
    add_order_by_argument(diff_parser)

    args = parser.parse_args()

    coloredlogs.install(level=logging.DEBUG, logger=LOGGER)

    def get_properties():
        # maintain user order
        properties = []
        for prop in args.select or []:
            for prop2 in [prop] if prop != '*' else list(Property):
                if prop2 not in properties:
                    properties.append(prop2)
        return properties

    def get_formatter() -> BaseFormatter:
        if not args.format:
            LOGGER.warning('output format is not specified')
            if sys.stdout.isatty():
                LOGGER.warning('STDOUT seems to be TTY, use table format')
                format = 'table'
            else:
                LOGGER.warning('STDOUT seems to be not TTY, use jsonl format')
                format = 'jsonl'
        else:
            format = args.format

        if format in FORMATS:
            return FORMATS[format]
        else:
            raise Exception('unknown format')

    try:
        container = load_snapshot(args.path)
        snapshot = container.data

        if args.action == 'list':
            result = query_list(
                snapshot, properties=get_properties())
        elif args.action == 'pandasql':
            result = query_pandas(
                snapshot, args.query)
        elif args.action == 'subordinates':
            result = query_subordinate_tree(
                snapshot, args.pattern, args.max_distance, args.min_distance,
                properties=get_properties())
        elif args.action == 'root-path':
            result = query_root_path(
                snapshot, args.pattern, properties=get_properties())
        elif args.action == 'diff':
            baseline_container = load_snapshot(args.baseline_path)
            baseline = baseline_container.data
            result = diff(snapshot, baseline, properties=get_properties())
        else:
            raise NotImplementedError

        # sort if requested
        if getattr(args, 'order_by', None):
            result = order_by(result, args.order_by)

        # format output
        formatter = get_formatter()
        formatter.format(result)
    except Exception as err:
        LOGGER.fatal('error! %s', err, exc_info=True)
        sys.exit(1)
