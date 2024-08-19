from textual.containers import Container
from textual.app import ComposeResult
from textual.widgets import (
    Static,
)
from textual.widget import Widget


class PlaceholderWidget(Widget):
    DEFAULT_CSS = """
#container {
    width: 40%;
    height: 30%;
    max-width: 100;
    background: $accent 50%;
    padding: 1
}

#text {
    content-align: center middle;
    height: 100%;
}
"""

    def __init__(self, *args, text, **kwargs):
        super().__init__(*args, **kwargs)
        self.text = text

    def compose(self) -> ComposeResult:
        self.styles.align = ('center', 'middle')
        yield Container(
            Static(self.text, id='text'),
            id='container'
        )
