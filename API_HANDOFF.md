# NoticeSaathi Backend API Handoff

## Base URL

http://127.0.0.1:5000

The Flask backend must be running before using these APIs.

## 1. Health check

GET /

Checks whether the backend is running.

## 2. Get categories

GET /categories

Returns all supported JEE Main notice categories.

## 3. Get all notices

GET /notices

Optional category filter:

GET /notices?category=admit_card

## 4. Get student-specific notices

GET /my-notices

Returns notices matching the student's saved category preferences.

## 5. Get preferences

GET /preferences

## 6. Save preferences

POST /preferences

Content-Type: application/json

Example body:

{
  "categories": ["result", "admit_card"]
}

Supported categories:

- application
- admit_card
- exam_city
- answer_key
- result
- correction
- schedule

## 7. Manually check for updates

POST /check-updates

Starts a manual check of the official JEE Main notices.

## 8. Get notification events

GET /notification-events

Optional parameters:

- unread_only=true
- personalized_only=true
- limit=50

Example:

GET /notification-events?unread_only=true&personalized_only=true

Returns new and updated notice events.

## 9. Mark notification as read

POST /notification-events/1/read

Replace 1 with the notification event ID.

## 10. Get scheduler status

GET /scheduler-status

Returns whether automatic monitoring is running and the next scheduled check.

## 11. Get latest monitoring status

GET /monitoring-status

Returns the latest monitoring run and scheduler information.

## 12. Get monitoring history

GET /monitoring-history

Optional parameter:

GET /monitoring-history?limit=10

## Notice object

A notice contains:

- id
- title
- url
- first_seen
- category

## Notification event object

An event contains:

- id
- notice_id
- event_type (new or updated)
- detected_at
- is_read
- title
- url
- category

## Important integration notes

- Use the backend base URL above during local development.
- The extension should use POST for /check-updates.
- The extension can use personalized_only=true to retrieve only events matching saved preferences.
- Always show the original notice URL so students can verify official information.
- Do not expose any future AI API key in extension JavaScript.
- The AI explanation feature is not yet implemented in this backend.
- For local testing, the backend must remain running.