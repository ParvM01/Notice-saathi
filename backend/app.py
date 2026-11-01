
from flask import Flask, jsonify
from scraper import fetch_notices
from database import (
    initialize_database,
    save_notice,
    get_all_notices
)

app = Flask(__name__)

# Create database when the server starts
initialize_database()


@app.route("/")
def home():
    return jsonify({
        "message": "NoticeSaathi Backend is running!",
        "project": "JEE Main Notice Monitor"
    })


@app.route("/notices")
def get_notices():
    notices = get_all_notices()

    return jsonify({
        "total": len(notices),
        "notices": notices
    })


@app.route("/check-updates", methods=["GET"])
def check_updates():
    latest_notices = fetch_notices()

    new_count = 0

    for notice in latest_notices:
        is_new = save_notice(
            notice["title"],
            notice["url"]
        )

        if is_new:
            new_count += 1

    return jsonify({
        "message": "Notice check completed!",
        "total_found": len(latest_notices),
        "new_notices": new_count
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
