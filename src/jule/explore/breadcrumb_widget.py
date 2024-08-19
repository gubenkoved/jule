from textual import on
from textual.app import ComposeResult
from textual.events import ScreenResume
from textual.widget import Widget
from textual.widgets import Static


class Breadcrumb(Widget):
    DEFAULT_CSS = """
Breadcrumb {
    dock: top;
    height: 1;
    width: 100%;
    background: $primary;
    color: $text;
    text-style: bold;
}
"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.container = Static()

    def compose(self) -> ComposeResult:
        yield self.container

    def on_mount(self):
        self.update()

    def update(self):
        titles = ['MAIN'] + [getattr(s, 'TITLE') or '???' for s in self.app._screen_stack[1:]]
        text = ' → '.join(titles)
        self.container.update(text)

    @on(ScreenResume)
    def on_screen_resume(self, _):
        self.update()
