import re
from collections import namedtuple

from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Key
from textual.keys import Keys
from textual.screen import ModalScreen
from textual.validation import Validator, ValidationResult
from textual.widgets import Input, Checkbox, Static

SearchModalScreenResult = namedtuple('SearchScreenResult', ['text', 'is_regex', 'is_case_sensitive'])


class RegexValidator(Validator):
    def validate(self, value: str) -> ValidationResult:
        try:
            re.compile(value)
            return self.success()
        except Exception as err:
            return self.failure('not a valid regex: %s' % err)


class SearchModalScreen(ModalScreen):
    CSS = """
#container {
    width: 60%;
    height: auto;
    padding: 2 3;
    background: $panel;
}

#options-container {
    layout: horizontal;
    height: auto;
    width: 100%;
}

#validation-errors {
    text-style: italic;
    color: $error;
    margin-top: 1;
    margin-left: 1;
}
"""

    REGEX_VALIDATOR = RegexValidator()

    def compose(self) -> ComposeResult:
        self.screen.styles.align = ('center', 'middle')

        yield Container(
            Input(
                id='input',
                validators=[],
            ),
            Static(),
            Container(
                Checkbox('regex', id='is-regex-checkbox'),
                Checkbox('case-sensitive', id='is-case-sensitive-checkbox'),
                id='options-container'
            ),
            Static(
                id='validation-errors',
            ),
            id='container'
        )

    def on_mount(self):
        self.query_one('#validation-errors').display = False

    def on_checkbox_changed(self, event: Checkbox.Changed):
        if event.checkbox.id == 'is-regex-checkbox':
            event.stop()

            input: Input = self.query_one('#input')

            if event.checkbox.value:
                input.validators.append(self.REGEX_VALIDATOR)
            else:
                input.validators.remove(self.REGEX_VALIDATOR)

            # cause reevaluation
            input.value += ' '
            input.value = input.value[:-1]

    def on_input_submitted(self, event: Input.Submitted):
        input: Input = self.query_one('#input')
        is_regex_checkbox: Checkbox = self.query_one('#is-regex-checkbox')
        is_case_sensitive_checkbox: Checkbox = self.query_one('#is-case-sensitive-checkbox')

        if not input.is_valid:
            self.notify('Input is not valid', title='SEARCH', severity='error')
            return

        self.dismiss(
            SearchModalScreenResult(
                event.input.value,
                is_regex_checkbox.value,
                is_case_sensitive_checkbox.value,
            )
        )

    def on_input_changed(self, event: Input.Changed) -> None:
        errors_static: Static = self.query_one('#validation-errors')

        if event.validation_result and not event.validation_result.is_valid:
            errors_static.update(
                '\n'.join(event.validation_result.failure_descriptions))
            errors_static.display = True
        else:
            errors_static.update('')
            errors_static.display = False

    def on_key(self, event: Key):
        if event.key == Keys.Escape:
            event.stop()
            self.dismiss(None)
