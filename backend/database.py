import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "notices.db"

CATEGORIES = {
    "application": [
        "application form", "registration", "apply online",
        "online application portal", "re-opening of online application",
        "reopening of online application"
    ],
    "admit_card": ["admit card", "hall ticket"],
    "exam_city": [
        "city intimation", "allotted exam city", "examination city",
        "allotment of examination city", "city of examination"
    ],
    "answer_key": ["answer key", "recorded responses", "response sheet"],
    "result": [
        "result", "score card", "scorecard", "nta scores",
        "declaration of the result",
        "declaration of joint entrance examination"
    ],
    "correction": [
        "correction window", "correction in application",
        "correction in particulars"
    ],
    "schedule": [
        "exam date", "examination schedule", "exam schedule",
        "dates of examination", "schedule of examination"
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
        cursor.execute(
            "UPDATE notices SET category = ? WHERE id = ?",
            (classify_notice(row["title"]), row["id"])
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notification_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            notice_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitoring_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL,
            total_found INTEGER NOT NULL DEFAULT 0,
            new_notices INTEGER NOT NULL DEFAULT 0,
            updated_notices INTEGER NOT NULL DEFAULT 0,
            baseline_created INTEGER NOT NULL DEFAULT 0,
            unchanged_notices INTEGER NOT NULL DEFAULT 0,
            hash_unavailable INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        )
    """)

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
    event_type = None

    if existing is None:
        cursor.execute("""
            INSERT INTO notices
            (title, url, category, content_hash)
            VALUES (?, ?, ?, ?)
        """, (title, url, category, content_hash))

        notice_id = cursor.lastrowid
        status = "new"
        event_type = "new"

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
            SET content_hash = ?, title = ?, category = ?
            WHERE id = ?
        """, (content_hash, title, category, existing["id"]))

        notice_id = existing["id"]
        status = "updated"
        event_type = "updated"

    else:
        status = "unchanged"

    if event_type:
        cursor.execute("""
            INSERT INTO notification_events
            (notice_id, event_type)
            SELECT ?, ?
            WHERE NOT EXISTS (
                SELECT 1
                FROM notification_events
                WHERE notice_id = ?
                  AND event_type = ?
                  AND detected_at >= datetime('now', '-2 seconds')
            )
        """, (notice_id, event_type, notice_id, event_type))

    connection.commit()
    connection.close()

    return status


def save_monitoring_run(result, status="success", error_message=None):
    connection = get_connection()

    connection.execute("""
        INSERT INTO monitoring_runs (
            status, total_found, new_notices, updated_notices,
            baseline_created, unchanged_notices, hash_unavailable,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        status,
        result.get("total_found", 0),
        result.get("new_notices", 0),
        result.get("updated_notices", 0),
        result.get("baseline_created", 0),
        result.get("unchanged_notices", 0),
        result.get("hash_unavailable", 0),
        error_message
    ))

    connection.commit()
    connection.close()


def get_latest_monitoring_run():
    connection = get_connection()

    row = connection.execute("""
        SELECT *
        FROM monitoring_runs
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    connection.close()
    return dict(row) if row else None


def get_monitoring_history(limit=10):
    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM monitoring_runs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()

    connection.close()
    return [dict(row) for row in rows]


def get_notification_events(
    unread_only=False,
    limit=50,
    categories=None
):
    connection = get_connection()

    conditions = []
    parameters = []

    if unread_only:
        conditions.append("e.is_read = 0")

    if categories is not None:
        if not categories:
            connection.close()
            return []

        placeholders = ",".join("?" for _ in categories)
        conditions.append(f"n.category IN ({placeholders})")
        parameters.extend(categories)

    query = """
        SELECT
            e.id,
            e.notice_id,
            e.event_type,
            e.detected_at,
            e.is_read,
            n.title,
            n.url,
            n.category
        FROM notification_events e
        JOIN notices n ON n.id = e.notice_id
    """

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY e.detected_at DESC, e.id DESC LIMIT ?"
    parameters.append(limit)

    rows = connection.execute(query, parameters).fetchall()
    events = [dict(row) for row in rows]

    connection.close()
    return events


def mark_notification_event_read(event_id):
    connection = get_connection()

    cursor = connection.execute("""
        UPDATE notification_events
        SET is_read = 1
        WHERE id = ?
    """, (event_id,))

    updated = cursor.rowcount > 0

    connection.commit()
    connection.close()
    return updated


def save_notice(title, url):
    connection = get_connection()
    category = classify_notice(title)

    cursor = connection.execute("""
        INSERT OR IGNORE INTO notices (title, url, category)
        VALUES (?, ?, ?)
    """, (title, url, category))

    is_new = cursor.rowcount > 0

    connection.commit()
    connection.close()
    return is_new


def get_all_notices(category=None):
    connection = get_connection()

    if category:
        rows = connection.execute("""
            SELECT id, title, url, first_seen, category
            FROM notices
            WHERE category = ?
            ORDER BY first_seen DESC
        """, (category,)).fetchall()
    else:
        rows = connection.execute("""
            SELECT id, title, url, first_seen, category
            FROM notices
            ORDER BY first_seen DESC
        """).fetchall()

    notices = [dict(row) for row in rows]

    connection.close()
    return notices


def get_preferences():
    connection = get_connection()

    row = connection.execute("""
        SELECT selected_categories
        FROM preferences
        WHERE id = 1
    """).fetchone()

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