from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from kanban_terminal.storage import BoardStorage


class BoardStorageMigrationTests(unittest.TestCase):
    def test_existing_database_is_migrated_for_waiting_for_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "kanban.db"
            self._create_legacy_database(db_path)

            storage = BoardStorage(db_path)
            waiting_task = storage.add_task("Needs reply", "waiting_for", body="Blocked on review")
            tasks = storage.list_tasks_by_status()

            self.assertEqual(waiting_task.status, "waiting_for")
            self.assertEqual([task.title for task in tasks["todo"]], ["Legacy task"])
            self.assertEqual([task.title for task in tasks["waiting_for"]], ["Needs reply"])

            with closing(sqlite3.connect(db_path)) as connection:
                schema_row = connection.execute(
                    """
                    SELECT sql
                    FROM sqlite_master
                    WHERE type = 'table' AND name = 'tasks'
                    """
                ).fetchone()

            self.assertIsNotNone(schema_row)
            self.assertIn("'waiting_for'", schema_row[0])

    @staticmethod
    def _create_legacy_database(db_path: Path) -> None:
        with closing(sqlite3.connect(db_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('todo', 'in_progress', 'done')),
                    sort_order INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX idx_tasks_status_sort
                ON tasks (status, sort_order, id);

                INSERT INTO tasks (title, status, sort_order)
                VALUES ('Legacy task', 'todo', 1);
                """
            )


if __name__ == "__main__":
    unittest.main()
