import { useCallback, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AccountContext } from "./account-context";
import { AccountSessionController } from "./account-session-controller";

export function AccountProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [controller] = useState(() => new AccountSessionController({ queryClient, onAccountChange: broadcastAccountChange }));
  const snapshot = useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getSnapshot);

  useEffect(() => {
    controller.activate();
    void controller.refresh().catch(() => {});
    const recheck = () => {
      if (document.visibilityState === "visible") void controller.refresh().catch(() => {});
    };
    globalThis.addEventListener("focus", recheck);
    document.addEventListener("visibilitychange", recheck);
    return () => {
      globalThis.removeEventListener("focus", recheck);
      document.removeEventListener("visibilitychange", recheck);
      controller.dispose();
    };
  }, [controller]);

  useEffect(() => {
    if (!snapshot.applicationId) return;
    const channel = openAccountChannel(snapshot.applicationId);
    if (!channel) return;
    channel.onmessage = event => {
      if (event.data === "changed") void controller.refresh({ announceChanges: false }).catch(() => {});
    };
    return () => channel.close();
  }, [controller, snapshot.applicationId]);

  const refresh = useCallback(() => controller.refresh(), [controller]);
  const changed = useCallback(() => controller.changed(), [controller]);

  return <AccountContext value={{ ...snapshot, api: controller.api, refresh, changed }}>{children}</AccountContext>;
}

function openAccountChannel(applicationId: string): BroadcastChannel | null {
  if (typeof BroadcastChannel === "undefined") return null;
  try {
    return new BroadcastChannel(`app-account-session:${applicationId}`);
  } catch {
    return null;
  }
}

function broadcastAccountChange(applicationId: string) {
  const channel = openAccountChannel(applicationId);
  if (!channel) return;
  try {
    channel.postMessage("changed");
  } catch {
    // Focus and visibility rechecks remain available when channel use is blocked.
  } finally {
    channel.close();
  }
}
