from dataclasses import dataclass

import requests
from rich.table import Table
from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, TabbedContent, TabPane, Label, Button, RichLog


# Global helper functions
def formatting_to_tags(tags: list[str], opening_tag: bool = None, closing_tag: bool = None) -> str:
    """Helper function for format_string"""
    buf = ""
    if opening_tag:
        for tag in tags:
            buf = buf + f"[{tag}]"

    elif closing_tag:
        for tag in tags:
            buf = buf + f"[/{tag}]"

    return buf


def format_string(content: str, tags: list[str]) -> str:
    """A helper function that wraps a content str in a set of Rich tags"""
    return formatting_to_tags(tags, opening_tag=True) + content + formatting_to_tags(tags, closing_tag=True)


def parse_content(content: list) -> str:
    """
    Parse the elements inside the 'content' JSON field of a frame. Translate into a Rich-readable string.
    """
    buf = ""
    for element in content:
        if type(element) is str:
            buf = buf + element
        elif type(element) is dict:
            buf = (
                buf
                + formatting_to_tags(element["formatting"], opening_tag=True)
                + element["value"]
                + formatting_to_tags(element["formatting"], closing_tag=True)
            )
    return buf


def input_type_to_regex(input_type: str, input_range: dict = None) -> str | None:
    if type(input_type) is not str:
        raise TypeError()

    if input_range is not None and type(input_range) is not dict:
        raise TypeError()

    match input_type:
        case "int":
            return r"[0-9]*"

        case "affirmative":
            return r"[y,n,Y,N]"

        case "str":
            return None

        case "any":
            return None

        case _:
            raise RuntimeError("Unknown Input Type!")


def get_content_from_frame(frame: dict) -> str:
    return parse_content(frame["components"]["content"])


def get_options_from_frame(frame: dict) -> list[str] | None:
    if "options" not in frame["components"] or frame["components"]["options"] is None:
        return None

    res = []

    for opt in frame["components"]["options"]:
        res.append(parse_content(opt))

    return res


# Global helper classes
@dataclass
class HistoryEntry:
    """
    A simple dataclass that holds a record for a previous game frame and the user's input
    """

    content: dict
    user_input: int | str


class HistoryWidget(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._frame_history = self.app.frame_history
        self._frame_index = self.app.current_history_index

    def compose(self) -> ComposeResult:
        yield Label("Some previous screen")
        yield Button("Back")
        yield Button("Forward")


class MainView(Static):
    """
    The main screen content for the app. Handles app switching and populating with elements
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        with TabbedContent(initial="game_view_tab", id="main_view_tabs"):
            with TabPane("Game", id="game_view_tab"):
                yield RichLog(id="game_view")
            with TabPane("History", id="history_tab"):
                yield HistoryWidget(id="history_view")
            with TabPane("Debug Log", id="debug_log_tab"):
                yield RichLog(name="Log", id="debug_log")


class TextualViewer(App):
    def __init__(self):
        super().__init__()

        self.frame_history: list[HistoryEntry] = []
        self.current_history_index: int | None = None
        self._ip = "http://localhost:8000"
        self._session = requests.Session()

    def _get_current_frame(self) -> dict:
        """
        Query the TXEnginePy server for the content for the current game frame
        """
        return self._session.get(self._ip, verify=False).json()

    def _submit_user_input(self, user_input: str | int | None) -> None:
        """
        Submit user's current input to the TXEnginePy server
        """
        true_input = user_input
        try:
            true_input = int(user_input)
        except TypeError:
            pass

        self._session.put(self._ip, params={"user_input": true_input}, verify=False)

    def _write_log(self, message: str) -> None:
        self.app.query_one("#debug_log", RichLog).write(message)

    @property
    def game_screen(self) -> RichLog:
        return self.query_one("#game_view", RichLog)

    @property
    def is_viewing_history(self) -> bool:
        return self.current_history_index is not None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(name="TXEngine")
        yield MainView(id="main_view")
        yield Input(id="primary_user_input")
        yield Footer()

    def action_show_tab(self, tab: str) -> None:
        """Switch to a new tab."""
        self.get_child_by_type(MainView).get_child_by_type(TabbedContent).active = tab

    @on(Input.Submitted)
    def submit_input(self, event: Input.Submitted) -> None:
        text = self.app.get_child_by_id("primary_user_input").value
        self._submit_user_input(text)
        self._write_log(f"Sent input: {text}")
        self.app.get_child_by_id("primary_user_input").value = ""
        frame = self._get_current_frame()
        text = get_content_from_frame(self._get_current_frame())

        self.game_screen.clear()
        self.game_screen.write(text)

        if get_options_from_frame(frame) is not None:
            table = Table()
            for col in frame["components"]["options_format"]["cols"]:
                table.add_column(col)

            for idx, row in enumerate(get_options_from_frame(frame)):
                table.add_row(str(idx), row)
            self.game_screen.write(table)


if __name__ == "__main__":
    app = TextualViewer()
    app.run()
