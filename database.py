import sqlite3
from pathlib import Path

DATABASE = Path(__file__).resolve().parent / "finance.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def execute(query, params=(), fetch=False):
    with get_connection() as connection:
        cursor = connection.execute(query, params)
        if fetch:
            return [dict(row) for row in cursor.fetchall()]
        connection.commit()
        return cursor.lastrowid
