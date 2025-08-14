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
        self.help_text: Widget = None

    def compose(self) -> ComposeResult:
        self.styles.align = ('center', 'middle')

        text_area = TextArea(id='query')
        text_area.cursor_blink = True

        # technically this is not correct as we use SQLite, but modern
        # tree-sitter is broken for dynamically defined languages
        # see https://github.com/grantjenks/py-tree-sitter-languages/issues/64
        # https://github.com/tree-sitter/py-tree-sitter/issues/303
        text_area.language = 'sql'

        queries_list_items = []
        for query_name in self.queries:
            list_item = ListItem(
                Static(query_name)
            )
            list_item.query_name = query_name
            queries_list_items.append(list_item)

        queries_list = ListView(id='queries', *queries_list_items)

        yield Container(
            Container(
                queries_list,
                id='left-dock'
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
