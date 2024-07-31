from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import (
    Markdown, )


# TODO: make help screen context aware
class HelpScreen(ModalScreen):
    TITLE = 'HELP'

    TEXT = """## Welcome to JULE!

Here is the least you can do with that:

* global employee count
* employee count by department
* find your colleague by name
* deadpool!
* ... and more

Have fun!

*Press ESC to go back*
"""

    CSS = """
.help {
    width: 80%;
    height: 80%;
    padding: 1 3;
}
"""

    BINDINGS = [
        ('escape', 'app.pop_screen', 'Pop screen')
    ]

    def compose(self) -> ComposeResult:
        self.styles.align = ('center', 'middle')

        yield Markdown(self.TEXT, classes='help')
