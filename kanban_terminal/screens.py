from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea


class TaskDetailsScreen(ModalScreen[tuple[str, str] | None]):
    CSS = """
    TaskDetailsScreen {
        align: center middle;
        background: rgba(6, 10, 18, 0.75);
    }

    #dialog {
        width: 62;
        height: 22;
        padding: 1 2;
        border: round #6ea8fe;
        background: #161b22;
    }

    #dialog-title {
        margin-bottom: 1;
        text-style: bold;
    }

    #dialog-actions {
        height: auto;
        margin-top: 1;
    }

    #error-message {
        color: indianred;
        height: 1;
    }

    #task-body {
        height: 1fr;
        margin-top: 1;
        border: round #334155;
    }

    Button {
        margin-right: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "submit", "Save"),
    ]

    def __init__(
        self,
        dialog_title: str,
        submit_label: str,
        initial_title: str = "",
        initial_body: str = "",
    ) -> None:
        super().__init__()
        self.dialog_title = dialog_title
        self.submit_label = submit_label
        self.initial_title = initial_title
        self.initial_body = initial_body

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.dialog_title, id="dialog-title")
            yield Input(placeholder="Write a short task title...", id="task-title")
            yield Label("Notes", id="body-label")
            yield TextArea(id="task-body")
            yield Static("", id="error-message")
            with Horizontal(id="dialog-actions"):
                yield Button("Cancel", id="cancel")
                yield Button(self.submit_label, id="submit", variant="primary")

    def on_mount(self) -> None:
        task_input = self.query_one("#task-title", Input)
        task_input.value = self.initial_title
        task_input.focus()
        task_input.cursor_position = len(self.initial_title)
        self.query_one("#task-body", TextArea).text = self.initial_body

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self._submit()
            return
        self.dismiss(None)

    def on_input_submitted(self, _: Input.Submitted) -> None:
        self._submit()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_submit(self) -> None:
        self._submit()

    def _submit(self) -> None:
        task_title = self.query_one("#task-title", Input).value.strip()
        task_body = self.query_one("#task-body", TextArea).text.strip()
        error_message = self.query_one("#error-message", Static)
        if not task_title:
            error_message.update("Please enter a task title before submitting.")
            return
        error_message.update("")
        self.dismiss((task_title, task_body))
