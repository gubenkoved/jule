import collections
import datetime
import functools
import os.path
import uuid
from typing import Dict

import pandas
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.events import Unmount
from textual.widget import Widget
from textual.widgets import DataTable

from jule.explore.data_table_searcher import DataTableSearcher
from jule.explore.search_screen import SearchModalScreen, SearchModalScreenResult


class DataFrameView(Widget):
    DEFAULT_CSS = """
DataFrameView DataTable {
    width: 100%;
    height: 100%;
}
"""
    BINDINGS = [
        ('f', 'find', 'Find'),
        ('ctrl+f', 'find_next', 'Find next'),
        ('e', 'export', 'Export'),
    ]

    # TODO: receive replacement map and sorter
    NULL_REPLACEMENT = Text('null', style='italic red')

    def __init__(self, *args, data_frame: pandas.DataFrame, export_dir='export', **kwargs):
        super().__init__(*args, **kwargs)
        self.sort_state: Dict[str, bool] = collections.defaultdict(lambda: False)
        self.data_frame: pandas.DataFrame = data_frame
        self.data_table = DataTable(zebra_stripes=True)
        self.searcher: DataTableSearcher = DataTableSearcher(self.data_table)
        self.search_modal_name = 'search-modal-' + str(uuid.uuid4())
        self.export_dir = export_dir

    def compose(self) -> ComposeResult:
        yield self.data_table

    def reset_for_new_data_table(self):
        self.sort_state.clear()

    def on_mount(self):
        for column in self.data_frame.columns.values.tolist():
            self.data_table.add_column(column)

        def render(val):
            if val is None:
                return self.NULL_REPLACEMENT
            return val

        for idx, record in enumerate(self.data_frame.values.tolist(), start=1):
            row = [render(val) for val in record]
            self.data_table.add_row(*row, label=str(idx))

        self.data_table.focus()

    def action_find(self):
        def check_exit(result: SearchModalScreenResult):
            if result is not None:
                self.searcher.search(
                    result.text, result.is_regex, result.is_case_sensitive)

        if not self.app.is_screen_installed(self.search_modal_name):
            self.app.install_screen(SearchModalScreen(), self.search_modal_name)

        self.app.push_screen(self.search_modal_name, check_exit)

    def action_find_next(self):
        self.searcher.search_next()

    def action_export(self):
        now = datetime.datetime.now()
        filename = '%s_%s.csv' % (now.strftime('%Y%m%d_%H%M%S'), str(uuid.uuid4())[:6])
        path = os.path.join(self.export_dir, filename)
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.data_frame.to_csv(path, header=True)
        self.notify('exported to %s' % os.path.abspath(path), title='EXPORT', severity='information')

    @staticmethod
    def safe_compare(v1, v2):
        def is_none(v):
            return v is None or v is DataFrameView.NULL_REPLACEMENT

        if is_none(v1) and is_none(v2):
            return 0

        if is_none(v1) and not is_none(v2):
            return -1

        if is_none(v2) and not is_none(v1):
            return 1

        assert v1 is not None and v2 is not None

        if v1 < v2:
            return -1
        elif v2 > v1:
            return 1
        else:
            return 0

    @on(DataTable.HeaderSelected)
    def on_data_table_header_clicker(self, event: DataTable.HeaderSelected):
        event.stop()

        # TODO: supply custom key, so that we can sort against "Text" being null replacement
        event.data_table.sort(
            event.column_key,
            reverse=self.sort_state[event.column_key.value],
            key=functools.cmp_to_key(self.safe_compare)
        )

        # flip the sort state
        self.sort_state[event.column_key.value] = not self.sort_state[event.column_key.value]

    @on(Unmount)
    def on_unmount(self, event: Unmount):
        if self.app.is_screen_installed(self.search_modal_name):
            self.app.uninstall_screen(self.search_modal_name)
