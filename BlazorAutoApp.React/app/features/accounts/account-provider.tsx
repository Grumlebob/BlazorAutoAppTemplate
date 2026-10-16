import { useCallback, useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AccountContext } from "./account-context";
import { AccountSessionController } from "./account-session-controller";

export function AccountProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [controller] = useState(() => new AccountSessionController({ queryClient }));
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
    if (!snapshot.applicationId || typeof BroadcastChannel === "undefined") return;
    const channel = new BroadcastChannel(`app-account-session:${snapshot.applicationId}`);
    channel.onmessage = event => {
      if (event.data === "changed") void controller.refresh().catch(() => {});
    };
    return () => channel.close();
  }, [controller, snapshot.applicationId]);

  const refresh = useCallback(() => controller.refresh(), [controller]);
  const changed = useCallback(async () => {
    const session = await controller.changed();
    if (snapshot.applicationId && typeof BroadcastChannel !== "undefined") {
      const channel = new BroadcastChannel(`app-account-session:${snapshot.applicationId}`);
      channel.postMessage("changed");
      channel.close();
    }
    return session;
  }, [controller, snapshot.applicationId]);

  return <AccountContext value={{ ...snapshot, api: controller.api, refresh, changed }}>{children}</AccountContext>;
}
