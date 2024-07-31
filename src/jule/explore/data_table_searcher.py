import re
from typing import Optional, Tuple

from textual.widgets import DataTable


# TODO: support highlight all matches somehow? need to modify DataTable cells then
#  which will require creating wrapper for cells that holds styled text and value
#  as well for sorting and searches
class DataTableSearcher:
    def __init__(self, data_table: DataTable):
        self.data_table: DataTable = data_table
        self.regex: Optional[re.Pattern] = None
        self.last_occurrence: Optional[Tuple[int, int]] = None

    def find_next_match(self, start_row: int = 0, start_col: int = 0):
        cols = len(self.data_table.columns)
        for row_idx in range(start_row, self.data_table.row_count):
            row_values = self.data_table.get_row_at(row_idx)
            for col_idx in range(cols):
                if row_idx == start_row and col_idx <= start_col:
                    continue
                if self.regex.search(str(row_values[col_idx])):
                    return row_idx, col_idx
        return None

    def search(self, target: str, is_regex: bool = False, is_case_sensitive: bool = False):
        flags = 0
        if not is_case_sensitive:
            flags = re.IGNORECASE

        if is_regex:
            self.regex = re.compile(target, flags=flags)
        else:
            self.regex = re.compile('.*' + re.escape(target) + '.*', flags=flags)

        match = self.find_next_match(0, -1)

        if match is not None:
            self.last_occurrence = match
            row_idx, col_idx = match
            self.data_table.move_cursor(row=row_idx, column=col_idx)
        else:
            self._notify('Unable to find')

    def search_next(self):
        if self.regex is None:
            self._notify('Find something first')
            return

        row_idx, col_idx = self.last_occurrence
        next_match = self.find_next_match(row_idx, col_idx)

        if next_match is not None:
            row_idx, col_idx = next_match
            self.last_occurrence = next_match
            self.data_table.move_cursor(row=row_idx, column=col_idx)
        else:
            self._notify('End of table')

    def _notify(self, text: str):
        self.data_table.notify(text, title='SEARCH')
