
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "notices.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_database():
    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


def save_notice(title, url):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO notices (title, url)
        VALUES (?, ?)
    """, (title, url))

    is_new = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return is_new


def get_all_notices():
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, title, url, first_seen
        FROM notices
        ORDER BY first_seen DESC
    """)

    notices = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return notices


if __name__ == "__main__":
    initialize_database()
    print("NoticeSaathi database initialized successfully!")
