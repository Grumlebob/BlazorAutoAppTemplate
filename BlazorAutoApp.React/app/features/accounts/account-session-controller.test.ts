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

  it("discards an old owner's private response when an ordinary refresh discovers a new owner", async () => {
    const privateResponse = deferred<Response>();
    const started = deferred<void>();
    let owner = "user-a";
    const queryClient = new QueryClient();
    const controller = createController(async request => {
      if (new URL(request.url).pathname === "/api/books") {
        started.resolve();
        return privateResponse.promise;
      }
      return accountResponse(request, owner, `csrf-${owner}`);
    }, queryClient);
    await controller.refresh();
    queryClient.setQueryData(["private", "user-a", "books"], { books: [{ title: "Alice's cached book" }] });
    queryClient.setQueryData(["public", "authors"], { authors: [{ name: "Public author" }] });
    const oldRequest = controller.api.GET("/api/books");
    await started.promise;

    owner = "user-b";
    await controller.refresh();
    privateResponse.resolve(json({ books: [{ id: 12, title: "Old owner's private book" }] }));

    await expect(oldRequest).rejects.toHaveProperty("name", "AbortError");
    expect(controller.getSnapshot().session.user?.id).toBe("user-b");
    expect(queryClient.getQueryData(["private", "user-a", "books"])).toBeUndefined();
    expect(queryClient.getQueryData(["public", "authors"])).toEqual({ authors: [{ name: "Public author" }] });
  });

  it.each(["GET", "POST"] as const)("keeps %s response bodies cancellable and discards success after an account change", async method => {
    const body = streamedJson();
    let owner = "user-a";
    let requestSignal: AbortSignal | undefined;
    const controller = createController(async request => {
      if (new URL(request.url).pathname === "/api/books") {
        requestSignal = request.signal;
        return body.response;
      }
      return accountResponse(request, owner, `csrf-${owner}`);
    });
    await controller.refresh();
    const oldRequest = method === "GET"
      ? controller.api.GET("/api/books")
      : controller.api.POST("/api/books", { body: { title: "Old owner's draft" } });
    await vi.waitFor(() => expect(body.response.bodyUsed).toBe(true));

    owner = "user-b";
    await controller.changed();
    const wasAborted = requestSignal?.aborted;
    body.complete({ books: [{ id: 12, title: "Old owner's private book" }] });

    await expect(oldRequest).rejects.toHaveProperty("name", "AbortError");
    expect(wasAborted).toBe(true);
    expect(controller.getSnapshot().session.user?.id).toBe("user-b");
  });

  it("does not let a late authentication error body invalidate the new owner's session", async () => {
    const body = streamedJson(401);
    const clone = vi.spyOn(body.response, "clone");
    let owner = "user-a";
    const fetcher = vi.fn(async (request: Request) => {
      if (new URL(request.url).pathname === "/api/books") return body.response;
      return accountResponse(request, owner, `csrf-${owner}`);
    });
    const controller = createController(fetcher);
    await controller.refresh();
    const oldRequest = controller.api.GET("/api/books");
    await vi.waitFor(() => expect(clone).toHaveBeenCalled());

    owner = "user-b";
    await controller.changed();
    const currentGeneration = controller.getSnapshot().generation;
    body.complete({ code: "AuthenticationRequired", title: "Sign-in required" });

    await expect(oldRequest).rejects.toHaveProperty("name", "AbortError");
    expect(controller.getSnapshot()).toMatchObject({
      generation: currentGeneration,
      status: "authenticated",
      session: { user: { id: "user-b" } },
    });
    expect(fetcher).toHaveBeenCalledTimes(5);
  });

  it("keeps a pending private request valid when a refresh confirms the same owner", async () => {
    const body = streamedJson();
    const controller = createController(async request => new URL(request.url).pathname === "/api/books"
      ? body.response : accountResponse(request, "user-a", "csrf-a"));
    await controller.refresh();
    const generation = controller.getSnapshot().generation;
    const request = controller.api.GET("/api/books");
    await vi.waitFor(() => expect(body.response.bodyUsed).toBe(true));
    await controller.refresh();
    body.complete({ books: [{ id: 12, title: "Current owner's book" }] });

    await expect(request).resolves.toMatchObject({ data: { books: [{ id: 12 }] } });
    expect(controller.getSnapshot().generation).toBe(generation);
  });

  it("discards pending private data when session discovery becomes unavailable", async () => {
    const body = streamedJson();
    let unavailable = false;
    const controller = createController(async request => {
      if (new URL(request.url).pathname === "/api/books") return body.response;
      return unavailable ? json({ title: "Unavailable" }, 503) : accountResponse(request, "user-a", "csrf-a");
    });
    await controller.refresh();
    const request = controller.api.GET("/api/books");
    await vi.waitFor(() => expect(body.response.bodyUsed).toBe(true));
    unavailable = true;
    await expect(controller.refresh()).rejects.toHaveProperty("status", 503);
    body.complete({ books: [{ id: 12, title: "Unavailable session's private book" }] });

    await expect(request).rejects.toHaveProperty("name", "AbortError");
    expect(controller.getSnapshot()).toMatchObject({ status: "unavailable", session: { user: null } });
  });

  it("discards private data when the application identity changes even if the user ID is equal", async () => {
    const body = streamedJson();
    let applicationId = applicationIdA;
    const controller = createController(async request => {
      const path = new URL(request.url).pathname;
      if (path === "/api/books") return body.response;
      if (path === "/api/client-config") return json({ schemaVersion: 1, accountsEnabled: true, applicationId });
      return accountResponse(request, "user-a", "csrf-a");
    });
    await controller.refresh();
    const request = controller.api.GET("/api/books");
    await vi.waitFor(() => expect(body.response.bodyUsed).toBe(true));
    applicationId = applicationIdB;
    await controller.refresh();
    body.complete({ books: [{ id: 12, title: "Other application's book" }] });

    await expect(request).rejects.toHaveProperty("name", "AbortError");
    expect(controller.getSnapshot()).toMatchObject({ applicationId: applicationIdB, status: "authenticated" });
  });
});

function createController(fetcher: (request: Request) => Promise<Response>, queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })): AccountSessionController {
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

function streamedJson(status = 200) {
  let stream!: ReadableStreamDefaultController<Uint8Array>;
  const response = new Response(new ReadableStream<Uint8Array>({ start(controller) { stream = controller; } }), {
    status,
    headers: { "content-type": status === 200 ? "application/json" : "application/problem+json" },
  });
  return {
    response,
    complete(body: unknown) {
      stream.enqueue(new TextEncoder().encode(JSON.stringify(body)));
      stream.close();
    },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}
