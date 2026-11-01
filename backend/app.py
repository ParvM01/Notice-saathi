from flask import Flask, jsonify, request

from scraper import fetch_notices
from database import (
    CATEGORIES,
    initialize_database,
    save_notice,
    get_all_notices,
    get_preferences,
    save_preferences
)

app = Flask(__name__)

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


@app.route("/preferences", methods=["GET"])
def read_preferences():
    return jsonify({
        "selected_categories": get_preferences()
    })


@app.route("/preferences", methods=["POST"])
def update_preferences():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request must contain JSON data"
        }), 400

    categories = data.get("categories")

    if not isinstance(categories, list):
        return jsonify({
            "error": "categories must be a list"
        }), 400

    if not all(isinstance(category, str) for category in categories):
        return jsonify({
            "error": "Every category must be a string"
        }), 400

    categories = list(dict.fromkeys(
        category.strip().lower()
        for category in categories
    ))

    valid_categories = list(CATEGORIES.keys())

    invalid_categories = [
        category for category in categories
        if category not in valid_categories
    ]

    if invalid_categories:
        return jsonify({
            "error": "Invalid categories",
            "invalid_categories": invalid_categories,
            "valid_categories": valid_categories
        }), 400

    save_preferences(categories)

    return jsonify({
        "message": "Preferences saved successfully!",
        "selected_categories": get_preferences()
    })


@app.route("/my-notices")
def get_my_notices():
    selected_categories = get_preferences()

    all_notices = get_all_notices()

    matching_notices = [
        notice for notice in all_notices
        if notice["category"] in selected_categories
    ]

    return jsonify({
        "total": len(matching_notices),
        "selected_categories": selected_categories,
        "notices": matching_notices
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