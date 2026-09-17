import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { push } from "../../lib/api";
import type { PushKey } from "../../lib/api/types";
import { Button } from "../ui/Button";

/** The VAPID key arrives base64url; PushManager wants the raw bytes. */
function toBytes(base64url: string): ArrayBuffer {
  const padded = base64url.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(padded + "=".repeat((4 - (padded.length % 4)) % 4));
  const bytes = new Uint8Array(new ArrayBuffer(binary.length));
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes.buffer;
}

function encode(buffer: ArrayBuffer | null): string {
  if (!buffer) return "";
  const binary = String.fromCharCode(...new Uint8Array(buffer));
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/**
 * Web Push (RF-NOT-002, RF-PWA-012).
 *
 * The permission prompt is only ever raised by the button below, never on load:
 * a prompt the member did not ask for is usually dismissed, and a dismissed one
 * does not come back. The button is hidden entirely when the instance has no
 * VAPID keys, so the app cannot ask for permission it could not act on.
 */
export function PushSettings() {
  const { t } = useTranslation();
  const [key, setKey] = useState<PushKey | null>(null);
  const [subscribed, setSubscribed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const supported =
    typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window;

  useEffect(() => {
    push
      .key()
      .then(setKey)
      .catch(() => setKey({ enabled: false, public_key: "" }));
    if (!supported) return;
    void navigator.serviceWorker.ready
      .then((registration) => registration.pushManager.getSubscription())
      .then((existing) => setSubscribed(Boolean(existing)))
      .catch(() => setSubscribed(false));
  }, [supported]);

  async function enable() {
    if (!key?.public_key) return;
    setBusy(true);
    setMessage(null);
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setMessage(t("push.denied"));
        return;
      }
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: toBytes(key.public_key),
      });
      await push.subscribe({
        endpoint: subscription.endpoint,
        p256dh: encode(subscription.getKey("p256dh")),
        auth: encode(subscription.getKey("auth")),
      });
      setSubscribed(true);
    } catch {
      setMessage(t("push.failed"));
    } finally {
      setBusy(false);
    }
  }

  async function disable() {
    setBusy(true);
    setMessage(null);
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await push.unsubscribe(subscription.endpoint);
        await subscription.unsubscribe();
      }
      setSubscribed(false);
    } catch {
      setMessage(t("push.failed"));
    } finally {
      setBusy(false);
    }
  }

  if (!key) return null;

  return (
    <section className="rounded-xl border border-line bg-raised p-5 shadow-sm">
      <h2 className="mb-1 font-semibold text-ink">{t("push.title")}</h2>
      <p className="mb-4 text-sm text-ink-muted">{t("push.description")}</p>

      {!key.enabled && <p className="text-sm text-ink-muted">{t("push.notConfigured")}</p>}
      {key.enabled && !supported && (
        <p className="text-sm text-ink-muted">{t("push.unsupported")}</p>
      )}
      {key.enabled && supported && (
        <>
          <p className="mb-3 text-sm text-ink-subtle">{t("push.iphoneHint")}</p>
          <Button
            variant={subscribed ? "secondary" : "primary"}
            disabled={busy}
            onClick={() => void (subscribed ? disable() : enable())}
          >
            {subscribed ? t("push.disable") : t("push.enable")}
          </Button>
        </>
      )}
      {message && <p className="mt-3 text-sm text-danger">{message}</p>}
    </section>
  );
}
