from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Static

from kanban_terminal.models import STATUS_LABELS, STATUS_ORDER, Task
from kanban_terminal.rendering import build_column_renderable
from kanban_terminal.screens import TaskDetailsScreen
from kanban_terminal.storage import BoardStorage


class ColumnView(Static):
    pass


class KanbanApp(App[None]):
    CSS = """
    Screen {
        background: #0f172a;
        color: #e2e8f0;
    }

    #board {
        height: 1fr;
        padding: 1;
    }

    ColumnView {
        width: 1fr;
        height: 1fr;
        padding: 0 1;
    }

    #help-bar {
        dock: bottom;
        padding: 1 2;
        background: #111827;
        color: #cbd5e1;
    }
    """

    TITLE = "Kanban Terminal"
    SUB_TITLE = "Colorful terminal workflow"

    BINDINGS = [
        Binding("a", "add_task", "Add task", show=True),
        Binding("e", "edit_task", "Edit task", show=True),
        Binding("left", "focus_left", "Prev column", show=False),
        Binding("right", "focus_right", "Next column", show=False),
        Binding("ctrl+left", "move_left", "Move left", show=False),
        Binding("ctrl+right", "move_right", "Move right", show=False),
        Binding("up", "select_previous", "Prev task", show=False),
        Binding("down", "select_next", "Next task", show=False),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, storage: BoardStorage) -> None:
        super().__init__()
        self.storage = storage
        self.active_status = STATUS_ORDER[0]
        self.selected_index_by_status = {status: 0 for status in STATUS_ORDER}
        self.tasks_by_status: dict[str, list[Task]] = {status: [] for status in STATUS_ORDER}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="board"):
            for status in STATUS_ORDER:
                yield ColumnView(id=f"column-{status}")
        yield Footer()
        yield Static(
            "Arrows switch columns and tasks. Press a to add, e to edit, and use Ctrl+Left/Ctrl+Right to move the selected task.",
            id="help-bar",
        )

    def on_mount(self) -> None:
        self.refresh_board()

    def action_add_task(self) -> None:
        self.push_screen(
            TaskDetailsScreen(
                dialog_title=f"Add a task to {STATUS_LABELS[self.active_status]}",
                submit_label="Add task",
            ),
            self._handle_task_created,
        )

    def action_edit_task(self) -> None:
        task = self._get_selected_task()
        if task is None:
            self.notify("Select a task before editing it.", severity="warning")
            return

        self.push_screen(
            TaskDetailsScreen(
                dialog_title=f"Edit task #{task.id}",
                submit_label="Save changes",
                initial_title=task.title,
                initial_body=task.body,
            ),
            self._handle_task_edited,
        )

    def action_focus_left(self) -> None:
        self._change_active_column(-1)

    def action_focus_right(self) -> None:
        self._change_active_column(1)

    def action_select_previous(self) -> None:
        tasks = self.tasks_by_status[self.active_status]
        if not tasks:
            self.notify("The active column does not have any tasks yet.", severity="warning")
            return
        current_index = self.selected_index_by_status[self.active_status]
        self.selected_index_by_status[self.active_status] = max(0, current_index - 1)
        self._render_columns()

    def action_select_next(self) -> None:
        tasks = self.tasks_by_status[self.active_status]
        if not tasks:
            self.notify("The active column does not have any tasks yet.", severity="warning")
            return
        current_index = self.selected_index_by_status[self.active_status]
        self.selected_index_by_status[self.active_status] = min(len(tasks) - 1, current_index + 1)
        self._render_columns()

    def action_move_left(self) -> None:
        self._move_selected_task(-1)

    def action_move_right(self) -> None:
        self._move_selected_task(1)

    def refresh_board(self) -> None:
        self.tasks_by_status = self.storage.list_tasks_by_status()
        self._normalize_selection()
        self._render_columns()

    def _handle_task_created(self, task_data: tuple[str, str] | None) -> None:
        if task_data is None:
            return

        task_title, task_body = task_data
        self.storage.add_task(task_title, self.active_status, body=task_body)
        self.refresh_board()
        self.selected_index_by_status[self.active_status] = len(self.tasks_by_status[self.active_status]) - 1
        self._normalize_selection()
        self._render_columns()
        self.notify(f"Added task to {STATUS_LABELS[self.active_status]}.")

    def _handle_task_edited(self, task_data: tuple[str, str] | None) -> None:
        if task_data is None:
            return

        task = self._get_selected_task()
        if task is None:
            self.notify("The selected task is no longer available.", severity="warning")
            return

        task_title, task_body = task_data
        self.storage.update_task(task.id, task_title, task_body)
        self.refresh_board()
        self.notify(f"Updated task #{task.id}.")

    def _change_active_column(self, direction: int) -> None:
        current_position = STATUS_ORDER.index(self.active_status)
        next_position = max(0, min(len(STATUS_ORDER) - 1, current_position + direction))
        self.active_status = STATUS_ORDER[next_position]
        self._normalize_selection()
        self._render_columns()

    def _move_selected_task(self, direction: int) -> None:
        task = self._get_selected_task()
        if task is None:
            self.notify("Select a task before moving it.", severity="warning")
            return

        current_position = STATUS_ORDER.index(self.active_status)
        next_position = current_position + direction
        if not 0 <= next_position < len(STATUS_ORDER):
            self.notify("That task is already at the edge of the board.", severity="warning")
            return

        target_status = STATUS_ORDER[next_position]
        self.storage.move_task(task.id, target_status)
        self.active_status = target_status
        self.refresh_board()
        self.selected_index_by_status[target_status] = len(self.tasks_by_status[target_status]) - 1
        self._normalize_selection()
        self._render_columns()
        self.notify(f"Moved '{task.title}' to {STATUS_LABELS[target_status]}.")

    def _get_selected_task(self) -> Task | None:
        tasks = self.tasks_by_status[self.active_status]
        if not tasks:
            return None
        selected_index = self.selected_index_by_status[self.active_status]
        return tasks[selected_index]

    def _normalize_selection(self) -> None:
        for status, tasks in self.tasks_by_status.items():
            if not tasks:
                self.selected_index_by_status[status] = 0
                continue
            self.selected_index_by_status[status] = min(
                self.selected_index_by_status[status],
                len(tasks) - 1,
            )

    def _render_columns(self) -> None:
        for status in STATUS_ORDER:
            self.query_one(f"#column-{status}", ColumnView).update(
                build_column_renderable(
                    status,
                    self.tasks_by_status[status],
                    is_active=status == self.active_status,
                    selected_index=self.selected_index_by_status[status],
                )
            )

