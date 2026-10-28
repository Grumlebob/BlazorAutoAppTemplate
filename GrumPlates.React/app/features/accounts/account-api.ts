import createClient from "openapi-fetch";
import type { components, paths } from "../../api/generated/schema";
import { ApiError, invalidApiResponse, normalizeTransportError, toHttpApiError } from "../../api/errors";

export type Session = components["schemas"]["AccountSession"];
export type ClientConfiguration = components["schemas"]["ClientConfiguration"];
export type AccountApi = Pick<ReturnType<typeof createClient<paths>>, "GET" | "POST" | "PUT" | "DELETE">;

export const disabledSession: Session = {
  enabled: false,
  registrationEnabled: false,
  emailEnabled: false,
  csrfToken: "",
  user: null,
};

export function createAccountApi(baseUrl: string, fetcher: (request: Request) => Promise<Response>) {
  return createClient<paths>({ baseUrl, credentials: "same-origin", fetch: fetcher });
}

export async function apiResult<T>(request: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  try {
    const result = await request;
    if (!result.response.ok) {
      throw toHttpApiError(result.response, result.error);
    }
    if (result.response.status !== 204 && result.data === undefined) {
      throw invalidApiResponse(result.response.status);
    }
    return result.data as T;
  } catch (error) {
    throw normalizeTransportError(error);
  }
}

export class AccountChangedError extends ApiError {
  constructor() {
    super({
      kind: "http",
      status: 409,
      title: "Account changed",
      message: "Your account changed. Refresh your session before continuing.",
    });
  }
}

export function safeReturnPath(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\") || Array.from(value).some(character => character.charCodeAt(0) < 32)) return "/my-books";
  const pathname = value.split(/[?#]/, 1)[0]?.toLowerCase();
  return pathname === "/my-books" || pathname === "/auth/settings" ? value : "/my-books";
}
