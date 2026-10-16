import { useCallback, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AccountContext } from "./account-context";
import { AccountSessionController } from "./account-session-controller";

export function AccountProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [changes] = useState(() => new AccountChangeChannel());
  const [controller] = useState(() => new AccountSessionController({ queryClient, onAccountChange: changes.announce }));
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
    return changes.connect(snapshot.applicationId, () => {
      void controller.refresh({ announceChanges: false }).catch(() => {});
    });
  }, [changes, controller, snapshot.applicationId]);

  const refresh = useCallback(() => controller.refresh(), [controller]);
  const changed = useCallback(() => controller.changed(), [controller]);

  return <AccountContext value={{ ...snapshot, api: controller.api, refresh, changed }}>{children}</AccountContext>;
}

class AccountChangeChannel {
  private channel: BroadcastChannel | null = null;

  readonly announce = (applicationId: string) => {
    if (this.channel?.name !== `app-account-session:${applicationId}`) return;
    try {
      this.channel.postMessage("changed");
    } catch {
      // Focus and visibility rechecks remain available when channel use is blocked.
    }
  };

  connect(applicationId: string, onChange: () => void): (() => void) | undefined {
    if (typeof BroadcastChannel === "undefined") return;
    let channel: BroadcastChannel;
    try {
      channel = new BroadcastChannel(`app-account-session:${applicationId}`);
    } catch {
      return;
    }
    this.channel = channel;
    channel.onmessage = event => {
      if (event.data === "changed") onChange();
    };
    return () => {
      if (this.channel === channel) this.channel = null;
      channel.close();
    };
  }
}

