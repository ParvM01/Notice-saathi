
from flask import Flask, jsonify, request

from scraper import fetch_notices
from database import (
    CATEGORIES,
    initialize_database,
    save_notice,
    get_all_notices
)

app = Flask(__name__)

# Initialise database when the server starts
initialize_database()


@app.route("/")
def home():
    return jsonify({
        "message": "NoticeSaathi Backend is running!",
        "project": "JEE Main Notice Monitor",
        "status": "active"
    })


@app.route("/categories")
def get_categories():
    categories = list(CATEGORIES.keys())
    categories.append("general")

    return jsonify({
        "total": len(categories),
        "categories": categories
    })


@app.route("/notices")
def get_notices():
    category = request.args.get("category")

    if category:
        category = category.strip().lower()

        valid_categories = list(CATEGORIES.keys()) + ["general"]

        if category not in valid_categories:
            return jsonify({
                "error": "Invalid category",
                "valid_categories": valid_categories
            }), 400

    notices = get_all_notices(category)

    return jsonify({
        "total": len(notices),
        "category": category or "all",
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
