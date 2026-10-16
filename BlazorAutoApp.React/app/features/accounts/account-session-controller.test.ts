import { QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, it, vi } from "vitest";
import { apiResult, disabledSession } from "./account-api";
import { AccountSessionController } from "./account-session-controller";

const controllers: AccountSessionController[] = [];
const clients: QueryClient[] = [];
const applicationIdA = "a".repeat(32);
const applicationIdB = "b".repeat(32);

afterEach(() => {
  controllers.splice(0).forEach(controller => controller.dispose());
  clients.splice(0).forEach(client => client.clear());
  vi.restoreAllMocks();
});

describe("account session controller", () => {
  it("uses explicit capability and treats an enabled session 404 as unavailable", async () => {
    const disabledRequests: Request[] = [];
    const disabledFetcher = vi.fn(async (request: Request) => {
      disabledRequests.push(request);
      return json({ schemaVersion: 1, accountsEnabled: false, applicationId: applicationIdA });
    });
    const disabled = createController(disabledFetcher);
    await expect(disabled.refresh()).resolves.toMatchObject({ enabled: false });
    expect(disabled.getSnapshot().status).toBe("disabled");
    expect(disabledFetcher).toHaveBeenCalledTimes(1);
    expect(disabledRequests[0]?.credentials).toBe("omit");

    const unavailableFetcher = vi.fn(async (request: Request) => {
      if (new URL(request.url).pathname === "/api/client-config") {
        return json({ schemaVersion: 1, accountsEnabled: true, applicationId: applicationIdB });
      }
      return json({ title: "Not found" }, 404, "application/problem+json");
    });
    const unavailable = createController(unavailableFetcher);
    await expect(unavailable.refresh()).rejects.toMatchObject({ status: 404 });
    expect(unavailable.getSnapshot()).toMatchObject({ status: "unavailable", applicationId: applicationIdB });
  });

  it("isolates account transports and attaches each captured owner and fresh CSRF token", async () => {
    const requestsA: Request[] = [];
    const requestsB: Request[] = [];
    const controllerA = createController(async request => {
      requestsA.push(request);
      return accountResponse(request, "user-a", "csrf-a");
    });
    const controllerB = createController(async request => {
      requestsB.push(request);
      return accountResponse(request, "user-b", "csrf-b");
    });
    await Promise.all([controllerA.refresh(), controllerB.refresh()]);

    await Promise.all([
      apiResult(controllerA.api.POST("/api/books", { body: { title: "A" } })),
      apiResult(controllerB.api.POST("/api/books", { body: { title: "B" } })),
    ]);

    const postA = requestsA.find(request => request.method === "POST");
    const postB = requestsB.find(request => request.method === "POST");
    expect(postA?.headers.get("X-Expected-User")).toBe("user-a");
    expect(postA?.headers.get("X-CSRF-TOKEN")).toBe("csrf-a");
    expect(postB?.headers.get("X-Expected-User")).toBe("user-b");
    expect(postB?.headers.get("X-CSRF-TOKEN")).toBe("csrf-b");
    expect(requestsA.some(request => request.headers.get("X-CSRF-TOKEN") === "csrf-b")).toBe(false);
    expect(requestsB.some(request => request.headers.get("X-CSRF-TOKEN") === "csrf-a")).toBe(false);
  });

  it("shares only one in-flight refresh per generation", async () => {
    const sessionResponse = deferred<Response>();
    const fetcher = vi.fn(async (request: Request) => {
      if (new URL(request.url).pathname === "/api/client-config") {
        return json({ schemaVersion: 1, accountsEnabled: true, applicationId: applicationIdA });
      }
      return sessionResponse.promise;
    });
    const controller = createController(fetcher);

    const first = controller.refresh();
    const second = controller.refresh();
    expect(first).toBe(second);
    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    sessionResponse.resolve(json(session("user-a", "csrf-a")));
    await Promise.all([first, second]);
  });

  it("does not let a stale refresh clear a newer generation's pending refresh", async () => {
    const oldConfiguration = deferred<Response>();
    const newSession = deferred<Response>();
    let configurationCalls = 0;
    const fetcher = vi.fn(async (request: Request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/client-config") {
        configurationCalls += 1;
        return configurationCalls === 1
          ? oldConfiguration.promise
          : json({ schemaVersion: 1, accountsEnabled: true, applicationId: applicationIdB });
      }
      return newSession.promise;
    });
    const controller = createController(fetcher);

    const stale = controller.refresh();
    const transition = controller.changed();
    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
    oldConfiguration.resolve(json({ schemaVersion: 1, accountsEnabled: true, applicationId: applicationIdA }));
    await expect(stale).rejects.toHaveProperty("name", "AbortError");

    const current = controller.refresh();
    expect(controller.refresh()).toBe(current);
    newSession.resolve(json(session("user-b", "csrf-b")));
    await Promise.all([transition, current]);
    expect(controller.getSnapshot()).toMatchObject({ status: "authenticated", session: { user: { id: "user-b" } } });
  });

  it("blocks a private mutation when the cookie owner changed after the request captured its owner", async () => {
    let owner = "user-a";
    const privateWrites: Request[] = [];
    const fetcher = vi.fn(async (request: Request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/books") privateWrites.push(request);
      return accountResponse(request, owner, `csrf-${owner}`);
    });
    const controller = createController(fetcher);
    await controller.refresh();
    owner = "user-b";

    await expect(apiResult(controller.api.POST("/api/books", { body: { title: "private" } })))
      .rejects.toMatchObject({ status: 409, message: expect.stringContaining("account changed") });
    expect(privateWrites).toHaveLength(0);
    expect(controller.getSnapshot().session.user?.id).toBe("user-b");
  });

  it("discards a successful private response that arrives after the session generation changes", async () => {
    const privateResponse = deferred<Response>();
    const requestStarted = deferred<void>();
    let owner = "user-a";
    const fetcher = vi.fn(async (request: Request) => {
      const path = new URL(request.url).pathname;
      if (path === "/api/books") {
        requestStarted.resolve();
        return privateResponse.promise;
      }
      return accountResponse(request, owner, `csrf-${owner}`);
    });
    const controller = createController(fetcher);
    await controller.refresh();

    const oldRequest = controller.api.GET("/api/books");
    await requestStarted.promise;
    owner = "user-b";
    await controller.changed();
    privateResponse.resolve(json({ books: [{ id: 12, title: "Old owner" }] }));

    await expect(oldRequest).rejects.toHaveProperty("name", "AbortError");
    expect(controller.getSnapshot().session.user?.id).toBe("user-b");
  });

  it("aborts and discards a pending refresh when the provider is disposed", async () => {
    const configuration = deferred<Response>();
    let requestSignal: AbortSignal | undefined;
    const fetcher = vi.fn(async (request: Request) => {
      requestSignal = request.signal;
      return configuration.promise;
    });
    const controller = createController(fetcher);
    controller.activate();
    const stale = controller.refresh();
    controller.dispose();

    expect(requestSignal?.aborted).toBe(true);
    configuration.resolve(json({ schemaVersion: 1, accountsEnabled: true, applicationId: applicationIdA }));
    await expect(stale).rejects.toHaveProperty("name", "AbortError");
    expect(controller.getSnapshot()).toMatchObject({ status: "loading", session: disabledSession });
  });
});

function createController(fetcher: (request: Request) => Promise<Response>): AccountSessionController {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  clients.push(queryClient);
  const controller = new AccountSessionController({ queryClient, baseUrl: "https://app.test", fetcher });
  controllers.push(controller);
  return controller;
}

function accountResponse(request: Request, userId: string, csrfToken: string): Response {
  const path = new URL(request.url).pathname;
  if (path === "/api/client-config") {
    return json({ schemaVersion: 1, accountsEnabled: true, applicationId: applicationIdA });
  }
  if (path === "/api/auth/session") return json(session(userId, csrfToken));
  if (path === "/api/books" && request.method === "GET") return json({ books: [] });
  if (path === "/api/books" && request.method === "POST") return json({ id: 1, title: "Saved" }, 201);
  return json({ title: "Not found" }, 404, "application/problem+json");
}

function session(userId: string, csrfToken: string) {
  return {
    enabled: true,
    registrationEnabled: true,
    emailEnabled: true,
    csrfToken,
    user: { id: userId, email: `${userId}@example.test`, roles: [] },
  };
}

function json(body: unknown, status = 200, contentType = "application/json") {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": contentType } });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}
