import functools
import os.path
from typing import List, Dict

import pandasql
from textual.app import ComposeResult
from textual.widgets import LoadingIndicator, Footer

from jule.explore.breadcrumb_widget import Breadcrumb
from jule.explore.common import (
    remove_empty_columns,
    construct_timeline_data,
    make_cached_diff_func,
    construct_data_frame_help_text,
)
from jule.explore.data_frame_view_widget import DataFrameView
from jule.explore.error_screen import ErrorScreen
from jule.explore.placeholder_widget import PlaceholderWidget
from jule.explore.query_picker_screen import QueryPickerScreen
from jule.explore.screen_base import ScreenBase
from jule.plugin import ExtractorBase
from jule.state import try_load

QUERY_PICKER_SCREEN_NAME = 'query-picker-for-changes-viewer'


def diff(
        extractor_class: type[ExtractorBase],
        data_dir: str, container_path: str, baseline_path: str) -> List[Dict]:
    current_container = try_load(container_path, load_data=True)
    baseline_container = try_load(baseline_path, load_data=True)

    assert current_container is not None
    assert baseline_container is not None

    current_extractor = extractor_class(current_container.data)
    baseline_extractor = extractor_class(baseline_container.data)

    baseline_entries = {
        entry_dn: entry_data
        for entry_dn, entry_data in baseline_container.data.entries
    }
    current_entries = {
        entry_dn: entry_data
        for entry_dn, entry_data in current_container.data.entries
    }

    result = []

    def extract_entry(entry_dn: str, extractor: ExtractorBase):
        return extractor.extract_all(entry_dn, skip_missing=True)

    for entry_dn, entry_data in current_entries.items():
        if entry_dn not in baseline_entries:
            continue

        new_data = extract_entry(entry_dn, current_extractor)
        old_data = extract_entry(entry_dn, baseline_extractor)

        common_props = set(new_data.keys()) & set(old_data.keys())

        updated_props = [
            prop for prop in common_props
            if new_data[prop] != old_data[prop]
        ]

        if not updated_props:
            continue

        # rename the fields
        old_data = {'old_' + prop: old_data[prop] for prop in old_data}

        result.append(dict(
            **new_data,
            **old_data,
            updated_props=', '.join(updated_props),
            path=os.path.relpath(container_path, data_dir),
            baseline_path=os.path.relpath(baseline_path, data_dir),
        ))

    return result


# TODO: mode where we diff only using FULL snapshots
class ChangesScreen(ScreenBase):
    TITLE = 'CHANGES'

    BINDINGS = [
        ('escape', 'app.pop_screen', 'Back'),
        ('p', "open_picker", 'Query'),
    ]

    CSS = """
#data {
    width: 100%;
    height: 100%;
}
"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_frame = None

    @property
    def plugin_queries(self):
        return {
            q.label: q.query_sql
            for q in self.plugin.changes_screen_queries
        }

    def compose(self) -> ComposeResult:
        yield Breadcrumb()
        yield Footer()
        yield LoadingIndicator(id='loader')

        self.app.install_screen(
            QueryPickerScreen(
                queries=self.plugin_queries,
            ), name=QUERY_PICKER_SCREEN_NAME
        )

    def action_open_picker(self):
        async def check_exit(query: str):
            await self.render_query(query)

        query_picker_screen: QueryPickerScreen = self.app.get_screen(
            QUERY_PICKER_SCREEN_NAME)

        if self.data_frame is not None:
            query_picker_screen.help_text = construct_data_frame_help_text(
                self.data_frame, accent_color=self.app.get_css_variables()['error'])

        query_picker_screen.update_help_text()
        self.app.push_screen(QUERY_PICKER_SCREEN_NAME, check_exit)

    def on_mount(self):
        self.app.run_worker(self.load_data, exclusive=True, thread=True)

    def hide_loader(self):
        self.query_one('#loader').display = False

    def load_data(self):
        self.data_frame = construct_timeline_data(
            self.settings.data_dir,
            diff_calculation_fn=make_cached_diff_func(
                cache_store=self.cache_store,
                cache_type='changes',
                inner_diff_func=functools.partial(
                    diff,
                    self.settings.plugin.property_extractor_class,
                    self.settings.data_dir)),
            )
        self.data_frame = remove_empty_columns(self.data_frame)

        self.app.call_from_thread(
            lambda: self.render_query(list(self.plugin_queries.values())[0])
        )

    async def render_query(self, query: str):
        assert self.data_frame is not None

        if len(self.data_frame) == 0:
            self.hide_loader()
            await self.mount(
                PlaceholderWidget(text='NO DATA AVAILABLE')
            )
            return

        try:
            result_frame = pandasql.sqldf(query, {
                'changes': self.data_frame,
            })
        except pandasql.PandaSQLException as err:
            self.hide_loader()
            await self.app.push_screen(
                ErrorScreen(error_message=str(err)),
            )
            return

        await self.query('#data').remove()

        frame_view = DataFrameView(
            id='data',
            data_frame=result_frame,
            export_dir=self.settings.export_dir,
        )

        self.hide_loader()
        await self.mount(frame_view)

        frame_view.focus()
