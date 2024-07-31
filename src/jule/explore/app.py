#! /usr/bin/env python3

import argparse
import logging
import os.path
import sys

import coloredlogs
from textual import on
from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Header, Footer, Static, ListView, ListItem

from jule import VERSION
from jule.cache import CacheStore
from jule.explore.changes_screen import ChangesScreen
from jule.explore.help_screen import HelpScreen
from jule.explore.settings import AppSettings
from jule.explore.snapshot_picker_screen import SnapshotPickerScreen
from jule.explore.timeline_screen import TimelineScreen
from jule.explore.under_construction_screen import UnderConstructionScreen
from jule.plugin import PluginBase, load_from_module, get_default_plugin_class_name

LOGGER = logging.getLogger(__name__)

APP_TITLE = 'JULE'
APP_VERSION = VERSION
APP_SUBTITLE = 'LDAP Explorer (ver %s)' % APP_VERSION


class ExplorerApp(App):
    TITLE = APP_TITLE
    SUB_TITLE = APP_SUBTITLE
    SCREENS = {
        'help': HelpScreen(),
        'under_construction': UnderConstructionScreen(),
    }
    BINDINGS = [
        ('t', 'toggle_dark', 'Toggle theme'),
        ('h', "push_screen('help')", 'Help'),
        ('q', 'quit', 'Quit'),
    ]

    CSS = """
#menu-header {
    width: 100%;
    content-align-horizontal: center;
    background: white 20%;
    padding: 1 3;
}

#menu-container {
    padding: 1 3;
    max-width: 60;
    height: auto;
}

ListView > ListItem {
    padding: 1 3;
}
"""

    def __init__(self, *args, settings: AppSettings, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings = settings
        self.cache_store = CacheStore(settings.cache_dir)

    @property
    def plugin(self) -> PluginBase:
        return self.settings.plugin

    def on_mount(self) -> None:
        self.screen.styles.align = ('center', 'middle')

    def compose(self) -> ComposeResult:
        header = Header()
        header.tall = True
        yield header
        yield Footer()

        menu_items_view = ListView(
            ListItem(Static('EXPLORE SNAPSHOT'), id='explore-view'),
            ListItem(Static('COMPARE SNAPSHOTS'), id='compare-view'),
            ListItem(Static('DEADPOOL / NEW HIRES'), id='timeline-view'),
            ListItem(Static('PROPERTIES CHANGES'), id='changes-view'),
            ListItem(Static('EXIT'), id='quit'),
        )
        menu_items_view.styles.height = 'auto'
        menu_items_view.focus()

        yield ScrollableContainer(
            Static('[b]MENU[/b]', id='menu-header'),
            menu_items_view,
            id='menu-container'
        )

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    @on(ListView.Selected)
    def on_menu_item(self, event):
        if event.item.id == 'explore-view':
            self.push_screen('snapshot_picker_screen')
        elif event.item.id == 'timeline-view':
            self.push_screen('timeline_screen')
        elif event.item.id == 'changes-view':
            self.push_screen('changes_screen')
        elif event.item.id == 'quit':
            self.exit()
        else:
            self.push_screen('under_construction')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=str, default='data')
    parser.add_argument('--cache-dir', type=str, default='cache')
    parser.add_argument('--export-dir', type=str, default='export')
    parser.add_argument('--log-path', type=str, default='explore.log')
    parser.add_argument('--plugin-module', type=str, default=get_default_plugin_class_name())
    args = parser.parse_args()

    logging.basicConfig(
        filename=args.log_path,
        filemode='a',
        format='%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.DEBUG)

    coloredlogs.install(level=logging.DEBUG)

    if not os.path.exists(args.cache_dir):
        LOGGER.warning('Cache dir does not exist -> creating')
        os.makedirs(args.cache_dir)

    try:
        LOGGER.debug('starting up')

        plugin = load_from_module(args.plugin_module)

        settings = AppSettings(
            data_dir=args.data_dir,
            cache_dir=args.cache_dir,
            export_dir=args.export_dir,
            plugin=plugin,
        )

        app = ExplorerApp(
            settings=settings,
        )

        app.install_screen(
            SnapshotPickerScreen(),
            'snapshot_picker_screen'
        )

        app.install_screen(
            TimelineScreen(),
            'timeline_screen'
        )

        app.install_screen(
            ChangesScreen(),
            'changes_screen'
        )

        app.run()

        LOGGER.debug('exit')
    except Exception as err:
        LOGGER.fatal('error! %s', err, exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
