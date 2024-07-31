from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import (
    Static, )


class UnderConstructionScreen(ModalScreen):
    TITLE = 'UNDER CONSTRUCTION'

    BINDINGS = [
        ('escape', 'app.pop_screen', 'Back'),
    ]

    CSS = """
#main {
    width: 40%;
    height: 30%;
    max-height: 10;
    max-width: 100;
}

#main Static {
    content-align: center middle;
    height: 100%;
    background: red 50%;
}
"""

    def compose(self) -> ComposeResult:
        self.styles.align = ('center', 'middle')
        yield Container(
            Static('UNDER CONSTRUCTION'),
            id='main'
        )
