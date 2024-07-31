import copy
from pathlib import Path
from typing import Dict

from textual import on
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Static, ListView, ListItem, TextArea,
)
from tree_sitter_languages import get_language


class QueryPickerScreen(ModalScreen):
    TITLE = 'QUERY PICKER'

    BINDINGS = [
        ('escape', 'app.pop_screen', 'Back'),
    ]

    CSS = """
#main {
    width: 80%;
    height: 80%;
}

#left-dock {
    dock: left;
    max_width: 40;
    width: 30%;
}

#right-container {
    layout: vertical;
}

#help-dock {
    dock: bottom;
    width: 100%;
    height: auto;
    padding: 1 2;
    content-align: center middle;
    background: $accent-lighten-3;
    color: $text;
}

#query {
    padding: 1 2;
}

ListView > ListItem {
    padding: 1 3;
}
"""

    def __init__(self, *args, queries: Dict[str, str], **kwargs):
        super().__init__(*args, **kwargs)
        self.queries = copy.deepcopy(queries)  # mutable
        self.orig_queries = copy.deepcopy(queries)  # immutable
        self.selected_query_name = list(queries.keys())[0]
        self.sqlite_lang = get_language('sqlite')
        self.sqlite_lang_highlight_query = (
                Path(__file__).parent.parent / 'data' / 'sqlite_highlights.scm'
        ).read_text()
        self.help_text: Widget = None

    def compose(self) -> ComposeResult:
        self.styles.align = ('center', 'middle')

        text_area = TextArea(id='query')
        text_area.cursor_blink = True
        text_area.register_language(self.sqlite_lang, self.sqlite_lang_highlight_query)
        text_area.language = 'sqlite'

        yield Container(
            Container(
                ListView(id='queries'), id='left-dock'
            ),
            Container(
                text_area,
                Container(
                    id='help-dock'
                ), id='right-container'
            ), id='main'
        )

    def on_mount(self):
        queries_list = self.query_one('#queries', expect_type=ListView)

        for query_name in self.queries:
            list_item = ListItem(
                Static(query_name)
            )
            list_item.query_name = query_name
            queries_list.append(list_item)

        queries_list.focus()
        self.update_help_text()

    # FIXME: hackish... find a normal way, issue is that Widget can be not yet
    #  mounted and then query will not return anything yet
    def update_help_text(self):
        if self.query('#help-dock'):
            container = self.query_one(
                '#help-dock', expect_type=Container)
            container.remove_children()

            if self.help_text:
                container.mount(self.help_text)

    @on(ListView.Highlighted)
    def on_query_item_highlighted(self, event: ListView.Highlighted):
        event.stop()

        if event.item is None:
            return

        query_name = event.item.query_name
        query_edit = self.query_one('#query', expect_type=TextArea)
        query_text = self.queries[query_name]
        query_edit.load_text(query_text)

        self.query_name = query_name

    @on(ListView.Selected)
    def on_query_item_selected(self, event: ListView.Selected):
        event.stop()
        query_name = event.item.query_name
        query = self.queries[query_name]
        self.dismiss(query)

    @on(TextArea.Changed)
    def on_text_area_text_change(self, event: TextArea.Changed):
        event.stop()
        self.queries[self.query_name] = event.text_area.text
