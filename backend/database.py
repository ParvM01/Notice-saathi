import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "notices.db"

CATEGORIES = {
    "application": [
        "application form",
        "registration",
        "apply online",
        "online application portal",
        "re-opening of online application",
        "reopening of online application"
    ],
    "admit_card": [
        "admit card",
        "hall ticket"
    ],
    "exam_city": [
        "city intimation",
        "allotted exam city",
        "examination city",
        "allotment of examination city",
        "city of examination"
    ],
    "answer_key": [
        "answer key",
        "recorded responses",
        "response sheet"
    ],
    "result": [
        "result",
        "score card",
        "scorecard",
        "nta scores",
        "declaration of the result",
        "declaration of joint entrance examination"
    ],
    "correction": [
        "correction window",
        "correction in application",
        "correction in particulars"
    ],
    "schedule": [
        "exam date",
        "examination schedule",
        "exam schedule",
        "dates of examination",
        "schedule of examination"
    ]
}


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def classify_notice(title):
    text = title.lower()

    for category, keywords in CATEGORIES.items():
        if any(keyword in text for keyword in keywords):
            return category

    return "general"


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

    columns = [
        row["name"]
        for row in cursor.execute(
            "PRAGMA table_info(notices)"
        ).fetchall()
    ]

    if "category" not in columns:
        cursor.execute("""
            ALTER TABLE notices
            ADD COLUMN category TEXT DEFAULT 'general'
        """)

    if "content_hash" not in columns:
        cursor.execute("""
            ALTER TABLE notices
            ADD COLUMN content_hash TEXT
        """)

    rows = cursor.execute(
        "SELECT id, title FROM notices"
    ).fetchall()

    for row in rows:
        category = classify_notice(row["title"])

        cursor.execute(
            "UPDATE notices SET category = ? WHERE id = ?",
            (category, row["id"])
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            selected_categories TEXT NOT NULL
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO preferences
        (id, selected_categories)
        VALUES (1, ?)
    """, (
        "application,admit_card,exam_city,answer_key,result,correction,schedule",
    ))

    connection.commit()
    connection.close()


def record_notice_check(title, url, content_hash):
    connection = get_connection()
    cursor = connection.cursor()

    category = classify_notice(title)

    cursor.execute(
        "SELECT id, content_hash FROM notices WHERE url = ?",
        (url,)
    )

    existing = cursor.fetchone()

    if existing is None:
        cursor.execute("""
            INSERT INTO notices
            (title, url, category, content_hash)
            VALUES (?, ?, ?, ?)
        """, (title, url, category, content_hash))

        status = "new"

    elif content_hash is None:
        status = "unavailable"

    elif existing["content_hash"] is None:
        cursor.execute("""
            UPDATE notices
            SET content_hash = ?
            WHERE id = ?
        """, (content_hash, existing["id"]))

        status = "baseline"

    elif existing["content_hash"] != content_hash:
        cursor.execute("""
            UPDATE notices
            SET content_hash = ?
            WHERE id = ?
        """, (content_hash, existing["id"]))

        status = "updated"

    else:
        status = "unchanged"

    connection.commit()
    connection.close()

    return status


def save_notice(title, url):
    connection = get_connection()
    cursor = connection.cursor()

    category = classify_notice(title)

    cursor.execute("""
        INSERT OR IGNORE INTO notices (title, url, category)
        VALUES (?, ?, ?)
    """, (title, url, category))

    is_new = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return is_new


def get_all_notices(category=None):
    connection = get_connection()
    cursor = connection.cursor()

    if category:
        cursor.execute("""
            SELECT id, title, url, first_seen, category
            FROM notices
            WHERE category = ?
            ORDER BY first_seen DESC
        """, (category,))
    else:
        cursor.execute("""
            SELECT id, title, url, first_seen, category
            FROM notices
            ORDER BY first_seen DESC
        """)

    notices = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return notices


def get_preferences():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT selected_categories
        FROM preferences
        WHERE id = 1
    """)

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return []

    return [
        category
        for category in row["selected_categories"].split(",")
        if category
    ]


def save_preferences(categories):
    connection = get_connection()

    selected_categories = ",".join(categories)

    connection.execute("""
        INSERT INTO preferences (id, selected_categories)
        VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET
        selected_categories = excluded.selected_categories
    """, (selected_categories,))

    connection.commit()
    connection.close()


if __name__ == "__main__":
    initialize_database()
    print("NoticeSaathi database initialized successfully!")