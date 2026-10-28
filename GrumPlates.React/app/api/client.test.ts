import { describe, expect, it, vi } from "vitest";
import { ApiError } from "./errors";
import { createPublicApi } from "./client";

const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });

describe("public API transport", () => {
  it("uses same-origin read paths, omits credentials, and passes cancellation", async () => {
    const controller = new AbortController();
    const fetcher = vi.fn(async (request: Request) => {
      expect(request.method).toBe("GET");
      return jsonResponse({ books: [] });
    });
    const api = createPublicApi({ baseUrl: "https://catalog.test", fetch: fetcher });

    await expect(api.listAuthorBooks({ signal: controller.signal })).resolves.toEqual({ books: [] });

    const request = fetcher.mock.calls[0]?.[0];
    expect(request?.url).toBe("https://catalog.test/api/author-books");
    expect(request?.credentials).toBe("omit");
    expect(request?.headers.has("authorization")).toBe(false);
    expect(request?.headers.has("x-csrf-token")).toBe(false);
    expect(request?.signal.aborted).toBe(false);
    controller.abort();
    expect(request?.signal.aborted).toBe(true);
  });

  it("maps a non-JSON HTTP failure without exposing its body", async () => {
    const fetcher = vi.fn(async (request: Request) => {
      expect(request.method).toBe("GET");
      return new Response("<html>internal proxy detail</html>", {
        status: 503,
        headers: {
          "content-type": "text/html",
          "retry-after": "900",
          "x-request-id": "request-456",
        },
      });
    });
    const api = createPublicApi({ baseUrl: "https://catalog.test", fetch: fetcher });

    const failure = await api.listAuthorBooks().then(
      () => undefined,
      (error: unknown) => error,
    );
    expect(failure).toMatchObject({
      kind: "http",
      status: 503,
      message: "The request failed (HTTP 503).",
      retryAfterMs: 60_000,
      correlationId: "request-456",
    });
    expect((failure as Error).message).not.toContain("internal proxy detail");
  });

  it("rejects empty, malformed, and non-JSON success responses with status", async () => {
    const responses = [
      new Response(null, { status: 200, headers: { "content-type": "application/json" } }),
      new Response("{broken", { status: 200, headers: { "content-type": "application/json" } }),
      new Response("<html>upstream</html>", { status: 200, headers: { "content-type": "text/html" } }),
      new Response(JSON.stringify({ title: "Problem" }), { status: 200, headers: { "content-type": "application/problem+json" } }),
    ];
    const fetcher = vi.fn(async (request: Request) => {
      expect(request.method).toBe("GET");
      return responses.shift() ?? jsonResponse({ books: [] });
    });
    const api = createPublicApi({ baseUrl: "https://catalog.test", fetch: fetcher });

    for (let index = 0; index < 4; index += 1) {
      const failure = await api.listAuthorBooks().then(
        () => undefined,
        (error: unknown) => error,
      );
      expect(failure).toMatchObject({
        kind: "invalid-response",
        status: 200,
        message: "The service returned an invalid response.",
      });
      expect((failure as Error).message).not.toContain("upstream");
    }
  });

  it("keeps cancellation intact and classifies unavailable network failures", async () => {
    const abort = new DOMException("Aborted", "AbortError");
    const abortedApi = createPublicApi({
      baseUrl: "https://catalog.test",
      fetch: async () => {
        throw abort;
      },
    });
    await expect(abortedApi.listAuthorBooks()).rejects.toBe(abort);

    const networkApi = createPublicApi({
      baseUrl: "https://catalog.test",
      fetch: async () => {
        throw new TypeError("Failed to fetch");
      },
    });
    await expect(networkApi.listAuthorBooks()).rejects.toMatchObject({
      kind: "network",
      message: "The catalog service is unavailable.",
    } satisfies Partial<ApiError>);
  });

  it("encodes generated path parameters and returns the generated response shape", async () => {
    const fetcher = vi.fn(async (request: Request) => {
      expect(request.method).toBe("GET");
      return jsonResponse({ id: 12, seedKey: "classic-12", title: "North and South", author: "Elizabeth Gaskell", url: null });
    });
    const api = createPublicApi({ baseUrl: "https://catalog.test", fetch: fetcher });

    await expect(api.getAuthorBook(12)).resolves.toMatchObject({
      id: 12,
      seedKey: "classic-12",
      title: "North and South",
    });
    expect(fetcher.mock.calls[0]?.[0].url).toBe("https://catalog.test/api/author-books/12");
  });
});
