from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import (
    Static, )


class ErrorScreen(ModalScreen):
    TITLE = 'ERROR'

    BINDINGS = [
        ('escape', 'app.pop_screen', 'Back'),
    ]

    CSS = """
#main {
    width: 40%;
    height: 30%;
    max-width: 100;
    background: red 50%;
    padding: 1
}

#error-header {
    content-align: center middle;
    margin-bottom: 1;
}

#error-text {
    content-align: center middle;
    height: 100%;
}
"""

    def __init__(self, *args, error_message=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_message = error_message or "Whoops, that's an error!"

    def compose(self) -> ComposeResult:
        self.styles.align = ('center', 'middle')
        yield Container(
            Static('[b]ERROR[/b]', id='error-header'),
            Static(self.error_message, id='error-text'),
            id='main'
        )
