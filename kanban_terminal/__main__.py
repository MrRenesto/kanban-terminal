from __future__ import annotations

import argparse
from pathlib import Path

from kanban_terminal.app import KanbanApp
from kanban_terminal.storage import BoardStorage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a colorful kanban board directly inside your terminal."
    )
    parser.add_argument(
        "--database",
        default="kanban.db",
        help="Path to the SQLite database file to use for persistence.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    storage = BoardStorage(Path(args.database).expanduser())
    app = KanbanApp(storage)
    app.run()


if __name__ == "__main__":
    main()
