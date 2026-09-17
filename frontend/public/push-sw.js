/* Push handling, imported into the service worker vite-plugin-pwa generates.
   Kept as its own file because generateSW writes the rest of the worker and
   would overwrite anything added to it directly. */

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    payload = {};
  }
  const title = payload.title || "Rodiva";
  event.waitUntil(
    self.registration.showNotification(title, {
      body: payload.body || "",
      icon: "/icons/pwa-light-192.png",
      badge: "/icons/favicon-48.png",
      // Same tag for the same record, so a reminder that fires twice replaces
      // its own notification instead of stacking up.
      tag: payload.url || "rodiva",
      data: { url: payload.url || "/" },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      // Reuse a tab that is already open rather than piling up new ones.
      for (const client of windows) {
        if ("focus" in client) {
          client.navigate(target);
          return client.focus();
        }
      }
      return self.clients.openWindow(target);
    }),
  );
});
