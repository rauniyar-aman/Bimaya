// Bimaya Web Push service worker.
//
// It does two things: show a notification when a push message arrives, and take
// the user to the right page when they click it. The payload is the small JSON
// the backend sends — { title, body, url } — nothing sensitive travels here.

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    // Fall back to plain text if the payload isn't JSON for some reason.
    payload = { title: "Bimaya", body: event.data ? event.data.text() : "" };
  }

  const title = payload.title || "Bimaya";
  const options = {
    body: payload.body || "",
    icon: "/bimaya-icon.png",
    badge: "/bimaya-icon.png",
    data: { url: payload.url || "/" },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const target = new URL(
    (event.notification.data && event.notification.data.url) || "/",
    self.location.origin,
  ).href;

  event.waitUntil(
    (async () => {
      const clients = await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });

      // Already on the exact page? Just focus it.
      for (const client of clients) {
        if (client.url === target && "focus" in client) return client.focus();
      }

      // Otherwise focus an open Bimaya tab and send it there.
      const open = clients.find((client) => "focus" in client);
      if (open) {
        await open.focus();
        if ("navigate" in open) {
          try {
            await open.navigate(target);
          } catch {
            /* navigation can fail across origins — ignore and leave focused */
          }
        }
        return;
      }

      // No tab open — open a new one.
      if (self.clients.openWindow) return self.clients.openWindow(target);
    })(),
  );
});
