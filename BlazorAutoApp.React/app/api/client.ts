import createClient from "openapi-fetch";
import type { components, paths } from "./generated/schema";
import { invalidApiResponse, isJsonSuccessContentType, normalizeTransportError, toHttpApiError } from "./errors";

export interface PublicApiClientOptions {
  /** Relative in the application; override only for isolated transport tests. */
  baseUrl?: string;
  fetch?: (request: Request) => Promise<Response>;
}

interface RequestOptions {
  signal?: AbortSignal;
}

type TextResult =
  | { data: string; error?: never; response: Response }
  | { data?: never; error: unknown; response: Response };

export function createPublicApi(options: PublicApiClientOptions = {}) {
  const client = createClient<paths>({
    baseUrl: options.baseUrl ?? "",
    credentials: "omit",
    fetch: options.fetch ?? ((request) => globalThis.fetch(request)),
  });

  return {
    async listAuthorBooks({ signal }: RequestOptions = {}) {
      const result = await requestJson<components["schemas"]["GetAuthorBooksResponse"]>(
        client.GET("/api/author-books", { signal, parseAs: "text" }),
      );
      return result;
    },

    async getAuthorBook(id: number | string, { signal }: RequestOptions = {}) {
      const result = await requestJson<components["schemas"]["GetAuthorBookResponse"]>(
        client.GET("/api/author-books/{id}", { params: { path: { id } }, signal, parseAs: "text" }),
      );
      return result;
    },
  };
}

async function requestJson<T>(request: Promise<TextResult>): Promise<T> {
  let result: TextResult;
  try {
    result = await request;
  } catch (error) {
    throw normalizeTransportError(error);
  }

  if (!result.response.ok) {
    throw toHttpApiError(result.response, "error" in result ? result.error : undefined);
  }

  if (!isJsonSuccessContentType(result.response.headers.get("content-type"))) {
    throw invalidApiResponse(result.response.status);
  }

  if (!("data" in result) || typeof result.data !== "string" || result.data.trim().length === 0) {
    throw invalidApiResponse(result.response.status);
  }

  try {
    // The generated OpenAPI contract supplies the response type; JSON parsing here only rejects empty or malformed bodies.
    return JSON.parse(result.data) as T;
  } catch (error) {
    throw invalidApiResponse(result.response.status, error);
  }
}

export const publicApi = createPublicApi();
