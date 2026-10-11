import { describe, expect, it } from "vitest";
import { ApiError } from "./errors";
import { queryClient } from "./query-client";

describe("public query defaults", () => {
  it("uses bounded transient caching and explicit retry behavior", () => {
    const options = queryClient.getDefaultOptions().queries;
    const retry = options?.retry;

    expect(options).toMatchObject({
      staleTime: 60_000,
      gcTime: 300_000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    });
    expect(typeof retry).toBe("function");

    if (typeof retry !== "function") {
      throw new Error("Expected an explicit query retry function.");
    }

    expect(retry(0, new ApiError({ kind: "network", message: "Unavailable" }))).toBe(true);
    expect(retry(1, new ApiError({ kind: "network", message: "Unavailable" }))).toBe(false);
    expect(retry(0, new ApiError({ kind: "http", status: 503, message: "Unavailable" }))).toBe(true);
    expect(retry(0, new ApiError({ kind: "http", status: 429, retryAfterMs: 30_000, message: "Rate limited" }))).toBe(false);
    expect(retry(0, new ApiError({ kind: "http", status: 500, message: "Server error" }))).toBe(false);
    expect(retry(0, new ApiError({ kind: "invalid-response", status: 200, message: "Invalid response" }))).toBe(false);
  });

  it("uses a bounded server retry delay when one is supplied", () => {
    const retryDelay = queryClient.getDefaultOptions().queries?.retryDelay;
    expect(typeof retryDelay).toBe("function");

    if (typeof retryDelay !== "function") {
      throw new Error("Expected an explicit query retry delay.");
    }

    expect(retryDelay(0, new ApiError({ kind: "http", status: 503, retryAfterMs: 60_000, message: "Unavailable" }))).toBe(60_000);
  });
});
