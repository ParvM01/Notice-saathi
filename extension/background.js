const API_BASE = "http://127.0.0.1:5000";
const ALARM_NAME = "check-notice-events";

async function checkForNoticeEvents() {
  try {
    const response = await fetch(
      `${API_BASE}/notification-events?unread_only=true&personalized_only=true`
    );

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const data = await response.json();

    for (const event of data.events || []) {
      const notificationId = `notice-event-${event.id}`;

      chrome.notifications.create(notificationId, {
        type: "basic",
        iconUrl: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/a4sAAAAASUVORK5CYII=",
        title: event.event_type === "updated"
          ? "NoticeSaathi: Notice updated"
          : "NoticeSaathi: New notice",
        message: event.title
      }, async () => {
        if (chrome.runtime.lastError) {
          console.error(chrome.runtime.lastError.message);
          return;
        }

        try {
          await fetch(`${API_BASE}/notification-events/${event.id}/read`, {
            method: "POST"
          });
        } catch (error) {
          console.error("Could not mark event as read:", error);
        }
      });
    }
  } catch (error) {
    console.error("NoticeSaathi notification check failed:", error);
  }
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(ALARM_NAME, { periodInMinutes: 15 });
  checkForNoticeEvents();
});

chrome.runtime.onStartup.addListener(checkForNoticeEvents);

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) {
    checkForNoticeEvents();
  }
});