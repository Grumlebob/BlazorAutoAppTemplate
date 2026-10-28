import createClient from "openapi-fetch";
import type { paths } from "./generated/schema";

export type ApiClient = Pick<ReturnType<typeof createClient<paths>>, "GET" | "POST" | "PUT" | "DELETE">;

export interface ApiClientOptions {
  baseUrl: string;
  credentials: RequestCredentials;
  fetch: (request: Request) => Promise<Response>;
}

export function createApiClient(options: ApiClientOptions) {
  return createClient<paths>(options);
}
