import { describe, expect, it } from "vitest";
import { ApiError, parseRetryAfter, toHttpApiError } from "./errors";

describe("public API errors", () => {
  it("normalizes safe problem details and validation fields", () => {
    const response = new Response(null, {
      status: 400,
      headers: {
        "content-type": "application/problem+json",
        "x-correlation-id": "req-123",
        "retry-after": "5",
      },
    });

    const error = toHttpApiError(response, {
      title: "Invalid request",
      detail: "The title is required.",
      errors: { title: ["Enter a title.", "<img src=x>"] },
    });

    expect(error).toMatchObject({
      kind: "http",
      status: 400,
      title: "Invalid request",
      detail: "The title is required.",
      fieldErrors: { title: ["Enter a title."] },
      retryAfterMs: 5_000,
      correlationId: "req-123",
    });
    expect(error.message).toBe("The title is required.");
  });

  it("does not copy upstream HTML or unsafe problem text into the message", () => {
    const response = new Response(null, { status: 503 });
    const error = toHttpApiError(response, "<html><body>secret</body></html>");

    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe("The request failed (HTTP 503).");
    expect(error.message).not.toContain("secret");
  });

  it("ignores JSON-shaped bodies sent with a non-JSON media type", () => {
    const response = new Response(null, { status: 503, headers: { "content-type": "text/html" } });
    const error = toHttpApiError(response, { title: "Internal proxy response", detail: "Private upstream detail" });

    expect(error.title).toBeUndefined();
    expect(error.detail).toBeUndefined();
    expect(error.message).toBe("The request failed (HTTP 503).");
  });

  it("bounds retry delays for seconds and HTTP dates", () => {
    const now = Date.parse("2026-10-11T00:00:00.000Z");

    expect(parseRetryAfter("999999", now)).toBe(60_000);
    expect(parseRetryAfter("invalid", now)).toBeUndefined();
    expect(parseRetryAfter("Sun, 11 Oct 2026 00:00:30 GMT", now)).toBe(30_000);
    expect(parseRetryAfter("Sun, 11 Oct 2026 00:00:00 GMT", now)).toBe(0);
  });
});
