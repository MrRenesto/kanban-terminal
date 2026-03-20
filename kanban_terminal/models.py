from __future__ import annotations

from dataclasses import dataclass
from typing import Final

STATUS_ORDER: Final[tuple[str, ...]] = ("todo", "in_progress", "waiting_for", "done")
STATUS_LABELS: Final[dict[str, str]] = {
    "todo": "Todo",
    "in_progress": "In Progress",
    "waiting_for": "Waiting For",
    "done": "Done",
}
STATUS_COLORS: Final[dict[str, str]] = {
    "todo": "#f59e0b",
    "in_progress": "magenta",
    "waiting_for": "purple",
    "done": "green",
}
SELECTED_COLOR: Final[str] = "#60a5fa"


@dataclass(slots=True, frozen=True)
class Task:
    id: int
    title: str
    body: str
    status: str
    sort_order: int
    created_at: str
    updated_at: str

