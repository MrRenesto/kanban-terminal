from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from kanban_terminal.models import STATUS_ORDER, Task


class BoardStorage:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                if not self._tasks_table_exists(connection):
                    self._create_tasks_table(connection)
                    return

                columns = self._get_tasks_columns(connection)
                if "body" not in columns or not self._tasks_table_supports_status(
                    connection, "waiting_for"
                ):
                    self._rebuild_tasks_table(connection, columns)
                self._ensure_tasks_index(connection)

    def list_tasks_by_status(self) -> dict[str, list[Task]]:
        grouped = {status: [] for status in STATUS_ORDER}
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT id, title, body, status, sort_order, created_at, updated_at
                FROM tasks
                ORDER BY
                    {self._status_order_case_sql()},
                    sort_order,
                    id
                """
            ).fetchall()

        for row in rows:
            grouped[row["status"]].append(self._row_to_task(row))
        return grouped

    def add_task(self, title: str, status: str, body: str = "") -> Task:
        self._validate_status(status)
        cleaned_title = title.strip()
        cleaned_body = body.strip()
        if not cleaned_title:
            raise ValueError("Task title cannot be empty.")

        with closing(self._connect()) as connection:
            with connection:
                next_sort_order = self._next_sort_order(connection, status)
                cursor = connection.execute(
                    """
                    INSERT INTO tasks (title, body, status, sort_order)
                    VALUES (?, ?, ?, ?)
                    """,
                    (cleaned_title, cleaned_body, status, next_sort_order),
                )
                row = connection.execute(
                    """
                    SELECT id, title, body, status, sort_order, created_at, updated_at
                    FROM tasks
                    WHERE id = ?
                    """,
                    (cursor.lastrowid,),
                ).fetchone()

        if row is None:
            raise RuntimeError("Task insert completed without a readable row.")
        return self._row_to_task(row)

    def move_task(self, task_id: int, new_status: str) -> None:
        self._validate_status(new_status)
        with closing(self._connect()) as connection:
            with connection:
                task = connection.execute(
                    "SELECT id, status FROM tasks WHERE id = ?",
                    (task_id,),
                ).fetchone()
                if task is None:
                    raise ValueError(f"Task {task_id} does not exist.")
                if task["status"] == new_status:
                    return

                next_sort_order = self._next_sort_order(connection, new_status)
                connection.execute(
                    """
                    UPDATE tasks
                    SET status = ?, sort_order = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (new_status, next_sort_order, task_id),
                )

    def update_task(self, task_id: int, title: str, body: str) -> None:
        cleaned_title = title.strip()
        cleaned_body = body.strip()
        if not cleaned_title:
            raise ValueError("Task title cannot be empty.")

        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    UPDATE tasks
                    SET title = ?, body = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (cleaned_title, cleaned_body, task_id),
                )
                if cursor.rowcount == 0:
                    raise ValueError(f"Task {task_id} does not exist.")

    def _next_sort_order(self, connection: sqlite3.Connection, status: str) -> int:
        row = connection.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_value FROM tasks WHERE status = ?",
            (status,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Unable to determine the next task order.")
        return int(row["next_value"])

    def _validate_status(self, status: str) -> None:
        if status not in STATUS_ORDER:
            raise ValueError(f"Unsupported task status: {status}")

    def _tasks_table_exists(self, connection: sqlite3.Connection) -> bool:
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'tasks'
            """
        ).fetchone()
        return row is not None

    def _get_tasks_columns(self, connection: sqlite3.Connection) -> set[str]:
        return {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
        }

    def _create_tasks_table(self, connection: sqlite3.Connection) -> None:
        connection.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL CHECK (status IN ({self._status_check_sql()})),
                sort_order INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_status_sort
            ON tasks (status, sort_order, id);
            """
        )

    def _ensure_tasks_index(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_status_sort
            ON tasks (status, sort_order, id)
            """
        )

    def _tasks_table_supports_status(
        self,
        connection: sqlite3.Connection,
        status: str,
    ) -> bool:
        row = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = 'tasks'
            """
        ).fetchone()
        return row is not None and f"'{status}'" in str(row["sql"])

    def _rebuild_tasks_table(
        self,
        connection: sqlite3.Connection,
        columns: set[str],
    ) -> None:
        body_select = "body" if "body" in columns else "'' AS body"
        connection.executescript(
            f"""
            ALTER TABLE tasks RENAME TO tasks_legacy;

            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL CHECK (status IN ({self._status_check_sql()})),
                sort_order INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            INSERT INTO tasks (id, title, body, status, sort_order, created_at, updated_at)
            SELECT id, title, {body_select}, status, sort_order, created_at, updated_at
            FROM tasks_legacy;

            DROP TABLE tasks_legacy;

            CREATE INDEX idx_tasks_status_sort
            ON tasks (status, sort_order, id);
            """
        )

    @staticmethod
    def _status_check_sql() -> str:
        return ", ".join(f"'{status}'" for status in STATUS_ORDER)

    @staticmethod
    def _status_order_case_sql() -> str:
        when_clauses = " ".join(
            f"WHEN '{status}' THEN {position}"
            for position, status in enumerate(STATUS_ORDER)
        )
        return f"CASE status {when_clauses} ELSE {len(STATUS_ORDER)} END"

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=int(row["id"]),
            title=str(row["title"]),
            body=str(row["body"]),
            status=str(row["status"]),
            sort_order=int(row["sort_order"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

