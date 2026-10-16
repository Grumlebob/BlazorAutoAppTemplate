import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useAccounts } from "./account-context";
import { AccountProvider } from "./account-provider";

const originalVisibilityDescriptor = Object.getOwnPropertyDescriptor(document, "visibilityState");

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  if (originalVisibilityDescriptor) Object.defineProperty(document, "visibilityState", originalVisibilityDescriptor);
});

describe("account provider lifecycle", () => {
  it("rechecks focus, visible state and app-scoped broadcasts, then removes listeners on unmount", async () => {
    const applicationId = "c".repeat(32);
    const requests: Request[] = [];
    const fetcher = vi.fn(async (request: Request) => {
      requests.push(request);
      const path = new URL(request.url).pathname;
      return path === "/api/client-config"
        ? json({ schemaVersion: 1, accountsEnabled: true, applicationId })
        : json({ enabled: true, registrationEnabled: false, emailEnabled: false, csrfToken: "csrf", user: null });
    });
    vi.stubGlobal("fetch", fetcher);
    vi.stubGlobal("BroadcastChannel", FakeBroadcastChannel);
    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });

    const queryClient = new QueryClient({ defaultOptions: { queries: { gcTime: 0 } } });
    const view = render(
      <QueryClientProvider client={queryClient}>
        <AccountProvider><SessionStatus /></AccountProvider>
      </QueryClientProvider>,
    );
    expect(await screen.findByTestId("account-status")).toHaveTextContent("anonymous");
    const sessionRequestCount = () => requests.filter(request => new URL(request.url).pathname === "/api/auth/session").length;
    await waitFor(() => expect(FakeBroadcastChannel.instances).toHaveLength(1));
    expect(FakeBroadcastChannel.instances[0]?.name).toBe(`app-account-session:${applicationId}`);

    window.dispatchEvent(new Event("focus"));
    await waitFor(() => expect(sessionRequestCount()).toBe(2));

    Object.defineProperty(document, "visibilityState", { configurable: true, value: "hidden" });
    document.dispatchEvent(new Event("visibilitychange"));
    await Promise.resolve();
    expect(sessionRequestCount()).toBe(2);

    Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
    document.dispatchEvent(new Event("visibilitychange"));
    await waitFor(() => expect(sessionRequestCount()).toBe(3));

    FakeBroadcastChannel.instances[0]!.onmessage?.({ data: "changed" } as MessageEvent);
    await waitFor(() => expect(sessionRequestCount()).toBe(4));

    view.unmount();
    expect(FakeBroadcastChannel.instances[0]?.closed).toBe(true);
    window.dispatchEvent(new Event("focus"));
    document.dispatchEvent(new Event("visibilitychange"));
    await Promise.resolve();
    expect(sessionRequestCount()).toBe(4);
    queryClient.clear();
  });
});

function SessionStatus() {
  const accounts = useAccounts();
  return <p data-testid="account-status">{accounts.status}</p>;
}

function json(value: unknown) {
  return new Response(JSON.stringify(value), { status: 200, headers: { "content-type": "application/json" } });
}

class FakeBroadcastChannel {
  static instances: FakeBroadcastChannel[] = [];
  onmessage: ((event: MessageEvent) => void) | null = null;
  closed = false;

  constructor(readonly name: string) {
    FakeBroadcastChannel.instances.push(this);
  }

  postMessage() {}

  close() {
    this.closed = true;
  }
}
