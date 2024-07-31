import collections
import datetime
import os
import os.path
from typing import List, Dict, Tuple, Callable, Optional

import pandas
from rich.text import Text, Style
from textual.widget import Widget
from textual.widgets import Static

from jule.cache import CacheStore, calculate_hash
from jule.state import LdapStorageContainer, LdapSnapshotMetadata, try_load


def human_size(size: int):
    if size <= 1024:
        return '%d B'
    elif size <= 1024 * 1024:
        return '%.0f KiB' % (size / 1024.0)
    else:
        return '%.1f MiB' % (size / 1024.0 / 1024.0)


def find_empty_columns(data_frame: pandas.DataFrame):
    return [
        col for col in data_frame.columns
        if data_frame[col].isnull().all()
    ]


def remove_empty_columns(data_frame: pandas.DataFrame):
    empty_columns = find_empty_columns(data_frame)

    if empty_columns:
        data_frame = data_frame.drop(columns=empty_columns)

    return data_frame


DIFF_FUNC = Callable[[str, str], List[Dict]]
FILTER_FUNC = Callable[[LdapSnapshotMetadata], bool]


def make_cached_diff_func(
        cache_store: CacheStore, cache_type: str, inner_diff_func: DIFF_FUNC):
    def cached_diff(container_path: str, baseline_path: str):
        cache_key = calculate_hash({
            'cache_type': cache_type,
            'container_path': container_path,
            'baseline_path': baseline_path,
        })
        value = cache_store.get(cache_key)

        if value is not None:
            return value

        value = inner_diff_func(container_path, baseline_path)
        cache_store.set(cache_key, value)
        return value

    return cached_diff


# TODO: bucket key function should be externally provided
def construct_timeline_data(
        data_dir: str,
        diff_calculation_fn: DIFF_FUNC,
        filter: Optional[FILTER_FUNC] = None) -> pandas.DataFrame:
    def timestamp_to_bucket_key(timestamp: float) -> str:
        dt = datetime.datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d')

    containers: List[Tuple[str, LdapStorageContainer]] = []

    for dir_path, dir_names, file_names in os.walk(data_dir):
        for file_name in file_names:
            path = os.path.join(dir_path, file_name)
            abs_path = os.path.abspath(path)

            container = try_load(abs_path, load_data=False)

            if container is None:
                continue

            if filter and not filter(container.metadata):
                continue

            containers.append((abs_path, container))

    buckets = collections.defaultdict(list)

    for path, container in containers:
        bucket_key = timestamp_to_bucket_key(container.metadata.timestamp)
        buckets[bucket_key].append((path, container))

    ordered_bucket_keys = sorted(buckets.keys())
    diff_entries = []

    def pick(items) -> str:
        abs_path, container = sorted(items, key=lambda t: t[1].metadata.timestamp)[0]
        return abs_path

    for idx in range(1, len(ordered_bucket_keys)):
        current_bucket_key = ordered_bucket_keys[idx]
        baseline_bucket_key = ordered_bucket_keys[idx - 1]
        diff_data = diff_calculation_fn(
            pick(buckets[current_bucket_key]),
            pick(buckets[baseline_bucket_key])
        )
        diff_entries.extend(
            [dict(entry, bucket_key=current_bucket_key) for entry in diff_data])

    data_frame = pandas.DataFrame.from_records(diff_entries)

    return data_frame


def construct_data_frame_help_text(data_frame: pandas.DataFrame, accent_color='red') -> Widget:
    empty_columns = find_empty_columns(data_frame)

    text = Text(no_wrap=False, overflow='fold')
    text.append('ALL COLUMNS: ', style='bold')

    for column_idx, column in enumerate(data_frame.columns):
        text.append(column)

        if column in empty_columns:
            text.append('*', style=accent_color)

        if column_idx != len(data_frame.columns) - 1:
            text.append(', ')

    if empty_columns:
        text.append('\n\n')
        text.append('*', style=Style(color=accent_color, bold=True))
        text.append(' NO DATA AVAILABLE')

    return Static(text)
