import logging
import threading

from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler

from scraper import fetch_notices, fetch_notice_hash
from ai_explainer import generate_notice_explanation

from database import (
    CATEGORIES,
    initialize_database,
    record_notice_check,
    get_all_notices,
    get_preferences,
    save_preferences,
    get_notification_events,
    mark_notification_event_read,
    save_monitoring_run,
    get_latest_monitoring_run,
    get_monitoring_history
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
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Vary"] = "Origin"

    return response


def run_notice_check():
    with check_lock:
        try:
            latest_notices = fetch_notices()

            if not latest_notices:
                error_message = (
                    "Could not retrieve notices from the official website."
                )

                result = {
                    "error": error_message,
                    "total_found": 0
                }

                save_monitoring_run(
                    result,
                    status="failed",
                    error_message=error_message
                )

                logging.error(error_message)
                return result

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

            if counts["hash_unavailable"] > 0:
                result["warning"] = (
                    "Some notice files could not be checked. "
                    "The monitoring run completed partially."
                )
                run_status = "partial"
            else:
                run_status = "success"

            save_monitoring_run(result, status=run_status)

            logging.info("Notice monitoring result: %s", result)
            return result

        except Exception as error:
            logging.exception("Notice monitoring failed")

            result = {
                "error": (
                    "An unexpected error occurred during notice monitoring."
                ),
                "total_found": 0
            }

            try:
                save_monitoring_run(
                    result,
                    status="failed",
                    error_message=str(error)
                )
            except Exception:
                logging.exception("Could not save failed monitoring run")

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


@app.route("/explain-notice", methods=["POST"])
def explain_notice():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request must contain JSON data"
        }), 400

    notice_id = data.get("notice_id")

    if (
        not isinstance(notice_id, int)
        or isinstance(notice_id, bool)
        or notice_id <= 0
    ):
        return jsonify({
            "error": "notice_id must be a positive integer"
        }), 400

    notices = get_all_notices()

    notice = next(
        (
            item for item in notices
            if item["id"] == notice_id
        ),
        None
    )

    if notice is None:
        return jsonify({
            "error": "Notice not found"
        }), 404

    try:
        explanation = generate_notice_explanation(notice)
        return jsonify(explanation)

    except Exception:
        logging.exception("Notice explanation failed")

        return jsonify({
            "error": "Could not generate notice explanation"
        }), 500


@app.route("/check-updates", methods=["POST"])
def check_updates():
    result = run_notice_check()

    if "error" in result:
        return jsonify(result), 502

    return jsonify(result)


@app.route("/notification-events", methods=["GET"])
def read_notification_events():
    unread_only = (
        request.args.get("unread_only", "false").lower()
        == "true"
    )

    personalized_only = (
        request.args.get("personalized_only", "false").lower()
        == "true"
    )

    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        return jsonify({
            "error": "limit must be a number"
        }), 400

    limit = max(1, min(limit, 100))

    selected_categories = (
        get_preferences() if personalized_only else None
    )

    events = get_notification_events(
        unread_only=unread_only,
        limit=limit,
        categories=selected_categories
    )

    return jsonify({
        "total": len(events),
        "unread_only": unread_only,
        "personalized_only": personalized_only,
        "selected_categories": (
            selected_categories if personalized_only else None
        ),
        "events": events
    })


@app.route(
    "/notification-events/<int:event_id>/read",
    methods=["POST"]
)
def mark_event_read(event_id):
    updated = mark_notification_event_read(event_id)

    if not updated:
        return jsonify({
            "error": "Notification event not found"
        }), 404

    return jsonify({
        "message": "Notification marked as read",
        "event_id": event_id
    })


@app.route("/scheduler-status")
def scheduler_status():
    job = scheduler.get_job("notice_monitor")

    return jsonify({
        "scheduler_running": scheduler.running,
        "monitoring_interval_minutes": 15,
        "next_check": (
            job.next_run_time.isoformat() if job else None
        )
    })


@app.route("/monitoring-status")
def monitoring_status():
    latest_run = get_latest_monitoring_run()
    job = scheduler.get_job("notice_monitor")

    return jsonify({
        "scheduler_running": scheduler.running,
        "monitoring_interval_minutes": 15,
        "next_scheduled_check": (
            job.next_run_time.isoformat() if job else None
        ),
        "last_run": latest_run
    })


@app.route("/monitoring-history")
def monitoring_history():
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        return jsonify({
            "error": "limit must be a number"
        }), 400

    limit = max(1, min(limit, 50))
    history = get_monitoring_history(limit)

    return jsonify({
        "total": len(history),
        "history": history
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

    logging.info(
        "Automatic JEE Main monitoring started (every 15 minutes)."
    )

    try:
        app.run(
            debug=True,
            port=5000,
            use_reloader=False
        )
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)