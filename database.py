"""
SQLite database layer for the Telegram Task Bot.
Stores users and tasks locally — no external services needed.
"""

import sqlite3
from datetime import date
from contextlib import contextmanager


DB_PATH = "tasks.db"


class Database:
    def __init__(self):
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id         INTEGER PRIMARY KEY,
                    name       TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    title      TEXT NOT NULL,
                    priority   TEXT DEFAULT 'medium',   -- high / medium / low
                    due_date   TEXT,                    -- YYYY-MM-DD or NULL
                    category   TEXT,
                    status     TEXT DEFAULT 'pending',  -- pending / done
                    created_at TEXT DEFAULT (datetime('now')),
                    done_at    TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
            """)

    # ── Users ─────────────────────────────────────────────────────────────────

    def ensure_user(self, user_id: int, name: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)",
                (user_id, name)
            )

    def get_all_users(self):
        with self._conn() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM users").fetchall()]

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def add_task(self, user_id: int, title: str, priority: str = "medium",
                 due_date: str = None, category: str = None) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO tasks (user_id, title, priority, due_date, category) VALUES (?, ?, ?, ?, ?)",
                (user_id, title, priority, due_date, category)
            )
            return cur.lastrowid

    def get_task(self, task_id: int):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return dict(row) if row else None

    def get_tasks(self, user_id: int, status: str = "pending", today_only: bool = False):
        with self._conn() as conn:
            query = "SELECT * FROM tasks WHERE user_id = ? AND status = ?"
            params = [user_id, status]
            if today_only:
                query += " AND date(done_at) = date('now')"
            query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, due_date ASC"
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def get_overdue_tasks(self, user_id: int):
        with self._conn() as conn:
            today = date.today().isoformat()
            rows = conn.execute(
                "SELECT * FROM tasks WHERE user_id = ? AND status = 'pending' AND due_date < ?",
                (user_id, today)
            ).fetchall()
            return [dict(r) for r in rows]

    def complete_task(self, task_id: int):
        with self._conn() as conn:
            conn.execute(
                "UPDATE tasks SET status = 'done', done_at = datetime('now') WHERE id = ?",
                (task_id,)
            )

    def delete_task(self, task_id: int):
        with self._conn() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def clear_done(self, user_id: int) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM tasks WHERE user_id = ? AND status = 'done'",
                (user_id,)
            )
            return cur.rowcount
