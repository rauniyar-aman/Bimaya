"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";

/**
 * Opt-in toggle for browser (Web Push) notifications, shown at the top of the
 * notifications page. It only does anything when the signed-in user's browser
 * supports push AND the backend has push switched on with a VAPID key; every
 * other case resolves to a plain, honest status line rather than an error.
 */
type Phase =
  | "checking" // working out support + backend availability + current state
  | "unsupported" // this browser can't do push
  | "unavailable" // backend push is off (dormant by default)
  | "denied" // the user blocked notifications in the browser
  | "off" // available, not subscribed on this device
  | "on" // subscribed on this device
  | "error"; // something went wrong

function browserSupportsPush(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

// A VAPID public key is base64url text; the Push API wants the raw bytes. The
// buffer is allocated explicitly as an ArrayBuffer so the result satisfies
// `applicationServerKey`'s BufferSource type.
function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const normalized = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(normalized);
  const buffer = new ArrayBuffer(raw.length);
  const output = new Uint8Array(buffer);
  for (let i = 0; i < raw.length; i += 1) output[i] = raw.charCodeAt(i);
  return output;
}

export function PushToggle() {
  const { isAuthenticated, authFetch } = useAuth();
  const [phase, setPhase] = useState<Phase>("checking");
  const [busy, setBusy] = useState(false);
  const [publicKey, setPublicKey] = useState("");

  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;

    async function init() {
      if (!browserSupportsPush()) {
        if (!cancelled) setPhase("unsupported");
        return;
      }
      try {
        const info = await api.notifications.pushVapidKey(authFetch);
        if (cancelled) return;
        if (!info.enabled || !info.public_key) {
          setPhase("unavailable");
          return;
        }
        setPublicKey(info.public_key);
        if (Notification.permission === "denied") {
          setPhase("denied");
          return;
        }
        // Are we already subscribed on this device?
        const registration = await navigator.serviceWorker.getRegistration();
        const existing = registration
          ? await registration.pushManager.getSubscription()
          : null;
        if (!cancelled) setPhase(existing ? "on" : "off");
      } catch {
        if (!cancelled) setPhase("error");
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, authFetch]);

  const enable = useCallback(async () => {
    setBusy(true);
    try {
      const registration = await navigator.serviceWorker.register("/sw.js");
      await navigator.serviceWorker.ready;

      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setPhase(permission === "denied" ? "denied" : "off");
        return;
      }

      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });
      await api.notifications.subscribePush(authFetch, subscription.toJSON());
      setPhase("on");
    } catch {
      setPhase("error");
    } finally {
      setBusy(false);
    }
  }, [authFetch, publicKey]);

  const disable = useCallback(async () => {
    setBusy(true);
    try {
      const registration = await navigator.serviceWorker.getRegistration();
      const subscription = registration
        ? await registration.pushManager.getSubscription()
        : null;
      if (subscription) {
        // Tell the backend first, then drop the browser subscription; failures
        // on either side shouldn't leave the toggle stuck.
        await api.notifications
          .unsubscribePush(authFetch, subscription.endpoint)
          .catch(() => {});
        await subscription.unsubscribe().catch(() => {});
      }
      setPhase("off");
    } catch {
      setPhase("error");
    } finally {
      setBusy(false);
    }
  }, [authFetch]);

  // Nothing to show until we know the state, and nothing useful to say when the
  // browser simply can't do push — stay out of the way in both cases.
  if (!isAuthenticated || phase === "checking" || phase === "unsupported") {
    return null;
  }

  const message: Record<Exclude<Phase, "checking" | "unsupported">, string> = {
    unavailable: "Browser notifications aren't switched on yet.",
    denied:
      "Notifications are blocked for this site. Turn them on in your browser settings to receive them.",
    off: "Get notified about policy, payment and claim updates even when Bimaya isn't open.",
    on: "You'll receive browser notifications on this device.",
    error: "We couldn't set up notifications just now. Please try again.",
  };

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-ink">
              Browser notifications
            </h2>
            {phase === "on" && (
              <span className="inline-flex items-center rounded-full border border-success-500 px-2 py-0.5 text-xs font-medium text-success-600">
                On
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted">{message[phase]}</p>
        </div>

        {(phase === "off" || phase === "error") && (
          <Button size="sm" onClick={enable} loading={busy}>
            Enable
          </Button>
        )}
        {phase === "on" && (
          <Button variant="secondary" size="sm" onClick={disable} loading={busy}>
            Turn off
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
