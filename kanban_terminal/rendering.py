from __future__ import annotations

from rich import box
from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from kanban_terminal.models import SELECTED_COLOR, STATUS_COLORS, STATUS_LABELS, Task


def build_column_renderable(
    status: str,
    tasks: list[Task],
    *,
    is_active: bool,
    selected_index: int,
) -> Panel:
    accent_color = STATUS_COLORS[status]

    if tasks:
        cards = [
            build_task_card(
                task=task,
                accent_color=accent_color,
                is_selected=is_active and index == selected_index,
            )
            for index, task in enumerate(tasks)
        ]
        content = Group(*cards)
    else:
        content = Align.center(
            Text("No tasks yet.\nPress a to create one.", style="dim"),
            vertical="middle",
        )

    title = f"{STATUS_LABELS[status]} ({len(tasks)})"
    subtitle = "Active column" if is_active else ""
    border_style = f"bold {SELECTED_COLOR}" if is_active else accent_color
    return Panel(
        content,
        title=title,
        subtitle=subtitle,
        border_style=border_style,
        box=box.ROUNDED,
        padding=(1, 1),
    )


def build_task_card(task: Task, accent_color: str, *, is_selected: bool) -> Panel:
    header = Text(task.title, style="bold white")
    metadata = Text(f"Task #{task.id}", style="dim")
    body_preview = Text(summarize_body(task.body), style="italic #cbd5e1")
    border_style = f"bold {SELECTED_COLOR}" if is_selected else accent_color
    return Panel(
        Group(header, metadata, body_preview),
        border_style=border_style,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def summarize_body(body: str) -> str:
    cleaned_body = " ".join(body.split())
    if not cleaned_body:
        return "No notes yet."
    if len(cleaned_body) <= 80:
        return cleaned_body
    return f"{cleaned_body[:77]}..."
