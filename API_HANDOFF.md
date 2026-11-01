# NoticeSaathi Backend API Handoff

## Base URL

http://127.0.0.1:5000

The Flask backend must be running before using these APIs.

## 1. Health check

GET /

## 2. Get categories

GET /categories

## 3. Get notices

GET /notices

Optional filter:

GET /notices?category=admit_card

## 4. Get personalized notices

GET /my-notices

Returns notices matching saved category preferences.

## 5. Get preferences

GET /preferences

## 6. Save preferences

POST /preferences

Content-Type: application/json

Example:

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

## 7. Explain a notice (temporary mock mode)

POST /explain-notice

Content-Type: application/json

Example:

{
  "notice_id": 1
}

Returns a structured Hinglish preview.

IMPORTANT:
- The current implementation uses mock mode.
- It does not analyse the actual PDF or notice contents.
- Gemini integration is pending.
- The response includes is_ai_generated: false.
- Always show the original official notice URL.

## 8. Manually check for updates

POST /check-updates

## 9. Get notification events

GET /notification-events

Optional parameters:

- unread_only=true
- personalized_only=true
- limit=50

Example:

GET /notification-events?unread_only=true&personalized_only=true

## 10. Mark notification as read

POST /notification-events/1/read

Replace 1 with the notification event ID.

## 11. Scheduler status

GET /scheduler-status

## 12. Latest monitoring status

GET /monitoring-status

## 13. Monitoring history

GET /monitoring-history

Optional:

GET /monitoring-history?limit=10

## Notice object

- id
- title
- url
- first_seen
- category

## Notification event object

- id
- notice_id
- event_type
- detected_at
- is_read
- title
- url
- category

## Integration notes

- Keep the backend running during local extension testing.
- The extension should use POST for /check-updates.
- Use personalized_only=true for personalized notification events.
- Never expose an AI API key in extension JavaScript.
- Store future Gemini credentials in backend environment variables.
- The current explanation endpoint is a mock preview, not a real AI feature.
- The actual notice PDF must be analysed before providing reliable AI explanations.