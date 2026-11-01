import logging
import threading

from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler

from scraper import fetch_notices, fetch_notice_hash

from database import (
    CATEGORIES,
    initialize_database,
    record_notice_check,
    get_all_notices,
    get_preferences,
    save_preferences
)

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

initialize_database()

scheduler = BackgroundScheduler()
check_lock = threading.Lock()


@app.after_request
def enable_extension_cors(response):
    origin = request.headers.get("Origin", "")

    if origin.startswith("chrome-extension://"):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Vary"] = "Origin"

    return response


def run_notice_check():
    with check_lock:
        latest_notices = fetch_notices()

        if not latest_notices:
            logging.error("Could not retrieve official JEE Main notices.")

            return {
                "error": "Could not retrieve notices from the official website.",
                "total_found": 0
            }

        counts = {
            "new_notices": 0,
            "updated_notices": 0,
            "baseline_created": 0,
            "unchanged_notices": 0,
            "hash_unavailable": 0
        }

        for notice in latest_notices:
            content_hash = fetch_notice_hash(notice["url"])

            status = record_notice_check(
                notice["title"],
                notice["url"],
                content_hash
            )

            if status == "new":
                counts["new_notices"] += 1

            elif status == "updated":
                counts["updated_notices"] += 1

            elif status == "baseline":
                counts["baseline_created"] += 1

            elif status == "unchanged":
                counts["unchanged_notices"] += 1

            elif status == "unavailable":
                counts["hash_unavailable"] += 1

        result = {
            "message": "Notice check completed!",
            "total_found": len(latest_notices),
            **counts
        }

        logging.info("Notice monitoring result: %s", result)

        return result


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


@app.route("/check-updates", methods=["POST"])
def check_updates():
    result = run_notice_check()

    if "error" in result:
        return jsonify(result), 502

    return jsonify(result)


@app.route("/scheduler-status")
def scheduler_status():
    job = scheduler.get_job("notice_monitor")

    return jsonify({
        "scheduler_running": scheduler.running,
        "monitoring_interval_minutes": 15,
        "next_check": job.next_run_time.isoformat() if job else None
    })


if __name__ == "__main__":

    scheduler.add_job(
        run_notice_check,
        trigger="interval",
        minutes=15,
        id="notice_monitor",
        max_instances=1,
        coalesce=True,
        replace_existing=True
    )

    scheduler.start()

    logging.info("Automatic JEE Main monitoring started (every 15 minutes).")

    try:
        app.run(
            debug=True,
            port=5000,
            use_reloader=False
        )
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)