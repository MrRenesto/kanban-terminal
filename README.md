# Kanban Terminal

A colorful terminal kanban board built with Python, `Textual`, and SQLite.

## Features

- Four fixed columns: `Todo`, `In Progress`, `Waiting For`, and `Done`
- Keyboard-first task navigation
- Colored card and column rendering inside the terminal
- SQLite-backed persistence so tasks survive restarts
- Task titles plus a notes/body field for descriptions and details

## Run it

```powershell
python -m pip install -e .
python -m kanban_terminal
```

To use a custom database path:

```powershell
python -m kanban_terminal --database .\data\kanban.db
```

## Controls

- `a`: add a task to the active column
- `e`: edit the selected task
- `left` / `right`: change the active column
- `up` / `down`: change the selected task
- `ctrl+left` / `ctrl+right`: move the selected task left or right across the board
- `[` / `]`: move the selected task left or right across the board
- `ctrl+s`: save from the add/edit task dialog
- `q`: quit

## Project layout

- `kanban_terminal\app.py`: Textual application orchestration and interaction flow
- `kanban_terminal\screens.py`: modal screen UI for task add/edit flows
- `kanban_terminal\rendering.py`: Rich/Textual helpers for column and task card rendering
- `kanban_terminal\storage.py`: SQLite persistence layer
- `kanban_terminal\models.py`: shared task and status definitions

