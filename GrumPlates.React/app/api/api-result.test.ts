import { describe, expect, it } from "vitest";
import { createApiClient } from "./api-client";
import { apiResult } from "./api-result";

function clientReturning(body: string | null) {
  return createApiClient({
    baseUrl: "https://app.example.test",
    credentials: "omit",
    fetch: async () => new Response(body, {
      headers: { "content-type": "application/json", "content-length": String(body?.length ?? 0) },
    }),
  });
}

describe("generated API results", () => {
  it("rejects a successful response without the expected body", async () => {
    const api = clientReturning(null);

    await expect(apiResult(api.GET("/api/author-books"))).rejects.toMatchObject({
      kind: "invalid-response",
      status: 200,
    });
  });

  it("preserves the generated client's malformed JSON failure", async () => {
    const api = clientReturning("{invalid");

    await expect(apiResult(api.GET("/api/author-books"))).rejects.toBeInstanceOf(SyntaxError);
  });
});
