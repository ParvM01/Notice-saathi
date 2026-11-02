import hashlib
import re
import sqlite3
from database import get_connection, initialize_database, record_notice_check

DEMO_NOTICES = {
    "application": {
        "title": "[DEMO] JEE Main application form notice",
        "content": "Application portal: Open\nRegistration deadline: 30 November\nRequired documents: Photograph, signature, and identity proof\nInstructions: Submit the form online and keep the confirmation page."
    },
    "admit_card": {
        "title": "[DEMO] JEE Main admit card notice",
        "content": "Admit card status: Not released\nDownload instructions: Use the application number and date of birth when available.\nCandidates should verify their details after downloading."
    },
    "exam_city": {
        "title": "[DEMO] JEE Main city intimation notice",
        "content": "City intimation status: Not released\nThe city slip will provide the allotted examination city.\nCandidates should check the official portal for updates."
    },
    "answer_key": {
        "title": "[DEMO] JEE Main answer key notice",
        "content": "Answer key status: Not released\nThe provisional answer key and recorded responses will be available on the candidate portal.\nThe objection process will be described in the official notice."
    },
    "result": {
        "title": "[DEMO] JEE Main result notice",
        "content": "Result status: Not declared\nThe scorecard will be available through the official candidate login.\nCandidates should keep their login details ready."
    },
    "correction": {
        "title": "[DEMO] JEE Main correction window notice",
        "content": "Correction window status: Not open\nCandidates should review their submitted application carefully.\nPermitted fields and correction dates will be announced in the official notice."
    },
    "schedule": {
        "title": "[DEMO] JEE Main examination schedule notice",
        "content": "Examination schedule status: To be announced\nSession dates and examination timings will be published on the official portal.\nCandidates should check the schedule before making travel arrangements."
    }
}


def _hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _substantive_text(content):
    # Ignore formatting, case, and punctuation-only edits. Word/number changes count.
    return " ".join(re.findall(r"[a-z0-9]+", content.lower()))


def initialize_simulation():
    initialize_database()
    con = get_connection()
    con.execute("""
        CREATE TABLE IF NOT EXISTS demo_notice_content (
            category TEXT PRIMARY KEY,
            content TEXT NOT NULL
        )
    """)
    for category, item in DEMO_NOTICES.items():
        url = f"demo://noticesaathi/judges/{category}"
        con.execute("""
            INSERT OR IGNORE INTO demo_notice_content (category, content)
            VALUES (?, ?)
        """, (category, item["content"]))
        existing = con.execute("SELECT id FROM notices WHERE url = ?", (url,)).fetchone()
        if existing is None:
            con.execute("""
                INSERT INTO notices (title, url, category, content_hash)
                VALUES (?, ?, ?, ?)
            """, (item["title"], url, category, _hash(item["content"])))
    con.commit()
    con.close()


def get_demo_notices():
    con = get_connection()
    rows = con.execute("""
        SELECT category, content FROM demo_notice_content ORDER BY category
    """).fetchall()
    con.close()
    return [
        {"category": row["category"], "title": DEMO_NOTICES[row["category"]]["title"], "content": row["content"]}
        for row in rows
    ]


def update_demo_notice(category, new_content):
    if category not in DEMO_NOTICES:
        raise ValueError("Unknown demo category")
    if not isinstance(new_content, str) or not new_content.strip():
        raise ValueError("Notice content cannot be empty")
    if len(new_content) > 20000:
        raise ValueError("Notice content is too long (maximum 20,000 characters)")

    con = get_connection()
    row = con.execute(
        "SELECT content FROM demo_notice_content WHERE category = ?", (category,)
    ).fetchone()
    if row is None:
        con.close()
        raise ValueError("Demo notice is not initialized")

    old_content = row["content"]
    if _substantive_text(old_content) == _substantive_text(new_content):
        con.close()
        return {"changed": False, "significant": False, "message": "No substantive content change detected. No notification created."}

    item = DEMO_NOTICES[category]
    url = f"demo://noticesaathi/judges/{category}"
    con.close()

    # Reuse the exact change/event path used by live notice monitoring.
    status = record_notice_check(item["title"], url, _hash(new_content))

    con = get_connection()
    con.execute(
        "UPDATE demo_notice_content SET content = ? WHERE category = ?",
        (new_content, category)
    )
    con.commit()
    con.close()
    return {"changed": True, "significant": True, "status": status, "message": "Content amendment detected. Notification event created."}


def get_demo_events(limit=30):
    con = get_connection()
    rows = con.execute("""
        SELECT e.id, e.event_type, e.detected_at, e.is_read,
               n.title, n.category
        FROM notification_events e
        JOIN notices n ON n.id = e.notice_id
        WHERE n.url LIKE 'demo://noticesaathi/judges/%'
        ORDER BY e.id DESC LIMIT ?
    """, (limit,)).fetchall()
    con.close()
    return [dict(row) for row in rows]
