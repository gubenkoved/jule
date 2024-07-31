from typing import Optional

import pandas
import pandasql
from textual.app import ComposeResult
from textual.widgets import (
    Footer,
    LoadingIndicator,
)

from jule.explore.breadcrumb_widget import Breadcrumb
from jule.explore.common import construct_data_frame_help_text
from jule.explore.data_frame_view_widget import DataFrameView
from jule.explore.data_table_searcher import DataTableSearcher
from jule.explore.error_screen import ErrorScreen
from jule.explore.query_picker_screen import (
    QueryPickerScreen,
)
from jule.explore.screen_base import ScreenBase
from jule.state import LdapStorageContainer

QUERY_PICKER_SCREEN_NAME = 'query-picker-for-snapshot-viewer'
SEARCH_SCREEN_NAME = 'search-for-snapshot-viewer'


class SnapshotViewerScreen(ScreenBase):
    TITLE = 'SNAPSHOT VIEWER'

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

    def __init__(self, *args, ldap_container_path: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.ldap_container_path = ldap_container_path
        self.data_frame: Optional[pandas.DataFrame] = None

    @property
    def plugin_queries(self):
        return {
            q.label: q.query_sql
            for q in self.plugin.snapshot_screen_queries
        }

    def compose(self) -> ComposeResult:
        yield Breadcrumb()
        yield Footer()
        yield LoadingIndicator(id='loader')

    def on_mount(self):
        self.run_worker(self.load_data_frame, exclusive=True, thread=True)

        if self.app.is_screen_installed(QUERY_PICKER_SCREEN_NAME):
            self.app.uninstall_screen(QUERY_PICKER_SCREEN_NAME)

        self.app.install_screen(
            QueryPickerScreen(
                queries=self.plugin_queries,
            ), name=QUERY_PICKER_SCREEN_NAME
        )

    def action_open_picker(self):
        def check_exit(query: str):
            self.render_query(query)

        query_picker_screen: QueryPickerScreen = self.app.get_screen(
            QUERY_PICKER_SCREEN_NAME
        )

        if self.data_frame is not None:
            query_picker_screen.help_text = construct_data_frame_help_text(
                self.data_frame, accent_color=self.app.get_css_variables()['error'])

        query_picker_screen.update_help_text()
        self.app.push_screen(QUERY_PICKER_SCREEN_NAME, check_exit)

    def hide_loader(self):
        self.query_one('#loader').display = False

    def show_loader(self):
        self.query_one('#loader').display = True

    def load_data_frame(self):
        with open(self.ldap_container_path, 'rb') as f:
            ldap_container = LdapStorageContainer.load(f)

        extractor_class = self.settings.plugin.property_extractor_class

        ldap_extractor = extractor_class(
            ldap_container.data,
        )

        records = []
        for entry_dn in ldap_extractor.entry_by_dn:
            records.append(dict(
                ldap_extractor.extract_all(entry_dn),
                dn=entry_dn)
            )

        self.data_frame = pandas.DataFrame.from_records(records)

        # once we loaded the data we render default query
        self.app.call_from_thread(
            lambda: self.render_query(
                list(self.plugin_queries.values())[0],
            )
        )

    def render_query(self, query: str):
        self.show_loader()

        try:
            result_frame = pandasql.sqldf(query, {
                'entries': self.data_frame,
            })
        except pandasql.PandaSQLException as err:
            self.app.push_screen(
                ErrorScreen(error_message=str(err)),
            )
            return
        finally:
            self.hide_loader()

        self.query('#data').remove()

        frame_view: DataFrameView = DataFrameView(
            id='data',
            data_frame=result_frame,
            export_dir=self.settings.export_dir,
        )

        self.searcher = DataTableSearcher(frame_view.data_table)

        self.mount(frame_view)

        frame_view.focus()
