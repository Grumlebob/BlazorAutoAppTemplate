import { invalidApiResponse, normalizeTransportError, toHttpApiError } from "./errors";

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
