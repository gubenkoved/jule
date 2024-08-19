import datetime
import logging
import os
from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Footer,
    DataTable,
)

from jule.explore.breadcrumb_widget import Breadcrumb
from jule.explore.common import human_size
from jule.explore.settings import AppSettings
from jule.explore.snapshot_viewer_screen import SnapshotViewerScreen
from jule.state import LdapStorageContainer

LOGGER = logging.getLogger(__name__)


class SnapshotPickerScreen(Screen):
    TITLE = 'SNAPSHOT PICKER'

    BINDINGS = [
        ('escape', 'app.pop_screen', 'Back'),
    ]

    CSS = """
#picker {
    height: 100%;
}
"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def settings(self) -> AppSettings:
        return self.app.settings

    def compose(self) -> ComposeResult:
        yield Breadcrumb()
        yield Footer()

        self.styles.align_horizontal = 'center'

        table = DataTable(cursor_type='row', zebra_stripes=True, id='picker')

        table.add_column('FILENAME')
        table.add_column('DATE')
        table.add_column('LABEL')
        table.add_column('ENTRIES')
        table.add_column('SIZE')

        yield table

    def on_mount(self):
        base_path = os.path.abspath(self.settings.data_dir)
        items = []
        for dir_path, dir_names, filenames in os.walk(self.settings.data_dir):
            for filename in filenames:
                abs_path = os.path.abspath(os.path.join(dir_path, filename))
                rel_path = os.path.relpath(abs_path, base_path)
                container = self.try_load(abs_path)
                if container:
                    items.append(
                        (rel_path, abs_path, container)
                    )

        # sort snapshots by timestamp
        items.sort(key=lambda t: t[2].metadata.timestamp)

        table: DataTable = self.query_one('#picker')

        for idx, (rel_path, abs_path, container) in enumerate(items, start=1):
            meta = container.metadata
            date = datetime.datetime.fromtimestamp(meta.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            file_stat = os.stat(abs_path)

            table.add_row(*(
                rel_path,
                date,
                meta.label,
                meta.entries_count,
                human_size(file_stat.st_size),
            ), label=str(idx), key=abs_path)

        table.focus()

    def try_load(self, path) -> Optional[LdapStorageContainer]:
        try:
            with open(path, 'rb') as f:
                container = LdapStorageContainer.load(f, load_data=False)
                return container
        except Exception as err:
            LOGGER.warning('unable to load "%s" due to %s', err)
            return None

    @on(DataTable.RowSelected)
    def on_row_selected(self, event):
        snapshot_viewer_screen = SnapshotViewerScreen(
            ldap_container_path=event.row_key.value
        )
        self.app.push_screen(snapshot_viewer_screen)
