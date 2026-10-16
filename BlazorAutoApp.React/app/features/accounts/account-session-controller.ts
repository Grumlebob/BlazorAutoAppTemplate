import type { QueryClient } from "@tanstack/react-query";
import { ApiError, isAbortError, invalidApiResponse, toHttpApiError } from "../../api/errors";
import { accountChangedError, createAccountApi, disabledSession, type ClientConfiguration, type Session } from "./account-api";

export type AccountStatus = "loading" | "disabled" | "anonymous" | "authenticated" | "unavailable";

export interface AccountSnapshot {
  status: AccountStatus;
  session: Session;
  loading: boolean;
  checking: boolean;
  error: string | null;
  applicationId: string | null;
  generation: number;
}

export interface AccountSessionControllerOptions {
  queryClient: QueryClient;
  baseUrl?: string;
  fetcher?: (request: Request) => Promise<Response>;
}

const emptySnapshot: AccountSnapshot = {
  status: "loading",
  session: disabledSession,
  loading: true,
  checking: true,
  error: null,
  applicationId: null,
  generation: 0,
};

const privateAccountPaths = new Set([
  "/api/auth/logout",
  "/api/auth/logout-all",
  "/api/auth/change-password",
  "/api/auth/change-email",
  "/api/auth/export",
  "/api/auth/delete",
]);

export class AccountSessionController {
  readonly api;

  private readonly queryClient: QueryClient;
  private readonly baseUrl: string;
  private readonly fetcher: (request: Request) => Promise<Response>;
  private readonly listeners = new Set<() => void>();
  private readonly activeRequests = new Set<AbortController>();
  private readonly requestGenerations = new WeakMap<Request, number>();
  private snapshot = { ...emptySnapshot };
  private generation = 0;
  private pendingRefresh?: { generation: number; promise: Promise<Session> };
  private refreshController?: AbortController;
  private disposed = false;

  constructor(options: AccountSessionControllerOptions) {
    this.queryClient = options.queryClient;
    this.baseUrl = options.baseUrl ?? (typeof globalThis.location === "undefined" ? "http://localhost" : globalThis.location.origin);
    this.fetcher = options.fetcher ?? (request => globalThis.fetch(request));
    this.api = createAccountApi(this.baseUrl, request => this.sendApiRequest(request));
    this.api.use({
      onRequest: ({ request }) => this.prepareApiRequest(request),
      onResponse: ({ request, response }) => {
        void this.handleApiResponse(request, response);
        return response;
      },
    });
  }

  readonly getSnapshot = (): AccountSnapshot => this.snapshot;

  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  activate(): void {
    this.disposed = false;
  }

  refresh(): Promise<Session> {
    if (this.disposed) return Promise.reject(createAbortError());
    if (this.pendingRefresh?.generation === this.generation) return this.pendingRefresh.promise;

    const generation = this.generation;
    const abortController = new AbortController();
    this.refreshController = abortController;
    this.publish({ checking: true, error: null });

    const promise = this.loadSession(generation, abortController.signal)
      .catch(async error => {
        if (this.isCurrent(generation) && !isAbortError(error)) {
          await this.clearPrivateData();
          if (this.isCurrent(generation)) {
            this.publish({
              status: "unavailable",
              session: disabledSession,
              loading: false,
              checking: false,
              error: getSafeAccountError(error),
            });
          }
        }
        throw error;
      })
      .finally(() => {
        if (this.pendingRefresh?.promise === promise) this.pendingRefresh = undefined;
        if (this.refreshController === abortController) this.refreshController = undefined;
      });

    this.pendingRefresh = { generation, promise };
    return promise;
  }

  async changed(): Promise<Session> {
    if (this.disposed) throw createAbortError();
    this.advanceGeneration();
    this.publish({ checking: true, error: null });
    await this.clearPrivateData();
    return this.refresh();
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.advanceGeneration();
    void this.clearPrivateData();
    this.listeners.clear();
  }

  private async loadSession(generation: number, signal: AbortSignal): Promise<Session> {
    const configResponse = await this.fetchJson("/api/client-config", "omit", signal);
    const configuration = await this.readJson<ClientConfiguration>(configResponse);
    if (!isClientConfiguration(configuration)) throw invalidApiResponse(configResponse.status);
    if (!this.isCurrent(generation)) throw createAbortError();
    this.publish({ applicationId: configuration.applicationId });

    if (!configuration.accountsEnabled) {
      await this.publishSession(generation, "disabled", disabledSession);
      return disabledSession;
    }

    const sessionResponse = await this.fetchJson("/api/auth/session", "same-origin", signal);
    const session = await this.readJson<Session>(sessionResponse);
    if (!isEnabledSession(session)) throw invalidApiResponse(sessionResponse.status);
    await this.publishSession(generation, session.user ? "authenticated" : "anonymous", session);
    return session;
  }

  private async publishSession(generation: number, status: "disabled" | "anonymous" | "authenticated", session: Session): Promise<void> {
    if (!this.isCurrent(generation)) throw createAbortError();
    const previousUserId = this.snapshot.session.user?.id ?? null;
    const nextUserId = session.user?.id ?? null;
    if (previousUserId !== nextUserId) {
      await this.clearPrivateData();
      if (!this.isCurrent(generation)) throw createAbortError();
    }
    this.publish({ status, session, loading: false, checking: false, error: null });
  }

  private async fetchJson(path: string, credentials: RequestCredentials, signal: AbortSignal): Promise<Response> {
    const request = new Request(new URL(path, this.baseUrl), {
      method: "GET",
      credentials,
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal,
    });
    const response = await this.fetcher(request);
    if (!response.ok) throw await readHttpError(response);
    return response;
  }

  private async readJson<T>(response: Response): Promise<T> {
    if (!isJsonResponse(response)) throw invalidApiResponse(response.status);
    try {
      return await response.json() as T;
    } catch (error) {
      throw invalidApiResponse(response.status, error);
    }
  }

  private async prepareApiRequest(request: Request): Promise<Request> {
    const requestGeneration = this.generation;
    this.requestGenerations.set(request, requestGeneration);
    request.headers.set("Accept", "application/json");
    const path = new URL(request.url).pathname;
    const privateRequest = isPrivateRequest(path);
    const capturedOwner = request.headers.get("X-Expected-User") ?? this.snapshot.session.user?.id ?? null;

    if (privateRequest && capturedOwner !== null) {
      request.headers.set("X-Expected-User", capturedOwner);
    }

    if (request.method === "GET" || request.method === "HEAD") return request;

    const session = await this.refresh();
    if (request.signal.aborted || !this.isCurrent(requestGeneration)) throw createAbortError();
    if (privateRequest && capturedOwner !== (session.user?.id ?? null)) throw accountChangedError();
    if (!session.enabled || !session.csrfToken) {
      throw new ApiError({ kind: "http", status: 503, message: "The account service is unavailable." });
    }
    request.headers.set("X-CSRF-TOKEN", session.csrfToken);
    return request;
  }

  private async sendApiRequest(request: Request): Promise<Response> {
    const requestGeneration = this.requestGenerations.get(request) ?? this.generation;
    const abortController = new AbortController();
    const abortFromRequest = () => abortController.abort(request.signal.reason);
    if (request.signal.aborted) abortFromRequest();
    else request.signal.addEventListener("abort", abortFromRequest, { once: true });
    this.activeRequests.add(abortController);

    try {
      const outgoing = new Request(request, { signal: abortController.signal });
      const response = await this.fetcher(outgoing);
      if (!this.isCurrent(requestGeneration)) throw createAbortError();
      return response;
    } finally {
      request.signal.removeEventListener("abort", abortFromRequest);
      this.activeRequests.delete(abortController);
    }
  }

  private async handleApiResponse(request: Request, response: Response): Promise<void> {
    if ((response.status !== 401 && response.status !== 409) || !isPrivateRequest(new URL(request.url).pathname)) return;
    const code = await readProblemCode(response);
    if (code === "SessionExpired" || code === "AuthenticationRequired" || code === "AccountChanged") {
      await this.changed().catch(() => {});
    }
  }

  private async clearPrivateData(): Promise<void> {
    await this.queryClient.cancelQueries({ queryKey: ["private"] });
    this.queryClient.removeQueries({ queryKey: ["private"] });
  }

  private advanceGeneration(): void {
    this.generation += 1;
    this.refreshController?.abort();
    this.refreshController = undefined;
    this.pendingRefresh = undefined;
    for (const request of this.activeRequests) request.abort();
    this.activeRequests.clear();
    this.publish({ generation: this.generation });
  }

  private isCurrent(generation: number): boolean {
    return !this.disposed && generation === this.generation;
  }

  private publish(changes: Partial<AccountSnapshot>): void {
    if (this.disposed) return;
    this.snapshot = { ...this.snapshot, ...changes, generation: this.generation };
    for (const listener of this.listeners) listener();
  }
}

function isPrivateRequest(path: string): boolean {
  return path === "/api/books" || path.startsWith("/api/books/") || privateAccountPaths.has(path);
}

function isClientConfiguration(value: unknown): value is ClientConfiguration {
  if (!value || typeof value !== "object") return false;
  const configuration = value as Partial<ClientConfiguration>;
  return configuration.schemaVersion === 1
    && typeof configuration.accountsEnabled === "boolean"
    && typeof configuration.applicationId === "string"
    && /^[0-9a-f]{32}$/.test(configuration.applicationId);
}

function isEnabledSession(value: unknown): value is Session {
  if (!value || typeof value !== "object") return false;
  const session = value as Partial<Session>;
  if (session.enabled !== true || typeof session.registrationEnabled !== "boolean"
      || typeof session.emailEnabled !== "boolean" || typeof session.csrfToken !== "string"
      || session.csrfToken.length === 0) return false;
  if (session.user === null) return true;
  return !!session.user && typeof session.user.id === "string" && typeof session.user.email === "string"
    && Array.isArray(session.user.roles) && session.user.roles.every(role => typeof role === "string");
}

function isJsonResponse(response: Response): boolean {
  const contentType = response.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase();
  return contentType === "application/json" || (contentType?.startsWith("application/") === true && contentType.endsWith("+json"));
}

async function readHttpError(response: Response): Promise<ApiError> {
  let body: unknown;
  if (isJsonResponse(response)) {
    try {
      body = await response.clone().json();
    } catch {
      body = undefined;
    }
  }
  return toHttpApiError(response, body);
}

async function readProblemCode(response: Response): Promise<string | null> {
  if (!isJsonResponse(response)) return null;
  try {
    const body = await response.clone().json() as { code?: unknown };
    return typeof body.code === "string" ? body.code : null;
  } catch {
    return null;
  }
}

function getSafeAccountError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error && error.name === "AbortError") return "";
  return "The account service is unavailable.";
}

function createAbortError(): DOMException {
  return new DOMException("The account session changed.", "AbortError");
}
