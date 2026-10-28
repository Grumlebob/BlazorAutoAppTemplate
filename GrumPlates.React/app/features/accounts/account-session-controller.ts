import type { QueryClient } from "@tanstack/react-query";
import { createApiClient, type ApiClient } from "../../api/api-client";
import { ApiError, isAbortError, invalidApiResponse, isJsonContentType, toHttpApiError } from "../../api/errors";
import { AccountChangedError, disabledSession, type ClientConfiguration, type Session } from "./account-api";

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
  onAccountChange?: (applicationId: string) => void;
}

interface SessionRefreshAttempt {
  generation: number;
  announceChanges: boolean;
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
  readonly api: ApiClient;

  private readonly queryClient: QueryClient;
  private readonly baseUrl: string;
  private readonly fetcher: (request: Request) => Promise<Response>;
  private readonly onAccountChange?: (applicationId: string) => void;
  private readonly listeners = new Set<() => void>();
  private readonly activeRequests = new Set<AbortController>();
  private readonly accountMutationRequests = new Set<AbortController>();
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
    this.onAccountChange = options.onAccountChange;
    const api = createApiClient({
      baseUrl: this.baseUrl,
      credentials: "same-origin",
      fetch: request => this.sendApiRequest(request),
    });
    api.use({
      onRequest: ({ request }) => this.prepareApiRequest(request),
      onResponse: async ({ request, response }) => {
        await this.handleApiResponse(request, response);
        return response;
      },
    });
    this.api = {
      GET: this.guardApiMethod(api.GET),
      POST: this.guardApiMethod(api.POST, true),
      PUT: this.guardApiMethod(api.PUT),
      DELETE: this.guardApiMethod(api.DELETE),
    };
  }

  readonly getSnapshot = (): AccountSnapshot => this.snapshot;

  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  activate(): void {
    this.disposed = false;
  }

  refresh(options: { announceChanges?: boolean } = {}): Promise<Session> {
    if (this.disposed) return Promise.reject(createAbortError());
    if (this.pendingRefresh?.generation === this.generation) return this.pendingRefresh.promise;

    const attempt = { generation: this.generation, announceChanges: options.announceChanges !== false };
    const abortController = new AbortController();
    this.refreshController = abortController;
    this.publish({ checking: true, error: null });

    const promise = this.loadSession(attempt, abortController.signal)
      .catch(async error => {
        if (this.isCurrent(attempt.generation) && !isAbortError(error)) {
          const hadPrivateSession = this.snapshot.session.user !== null;
          this.advanceGeneration(attempt);
          await this.clearPrivateData();
          if (this.isCurrent(attempt.generation)) {
            this.publish({
              status: "unavailable",
              session: disabledSession,
              loading: false,
              checking: false,
              error: getSafeAccountError(error),
            });
            if (hadPrivateSession && attempt.announceChanges) this.signalAccountChange();
          }
        }
        throw error;
      })
      .finally(() => {
        if (this.pendingRefresh?.promise === promise) this.pendingRefresh = undefined;
        if (this.refreshController === abortController) this.refreshController = undefined;
      });

    this.pendingRefresh = { generation: attempt.generation, promise };
    return promise;
  }

  async changed(): Promise<Session> {
    if (this.disposed) throw createAbortError();
    this.advanceGeneration();
    this.publish({ checking: true, error: null });
    await this.clearPrivateData();
    this.signalAccountChange();
    return this.refresh({ announceChanges: false });
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.advanceGeneration(undefined, false);
    void this.clearPrivateData();
    this.listeners.clear();
  }

  private async loadSession(attempt: SessionRefreshAttempt, signal: AbortSignal): Promise<Session> {
    const configResponse = await this.fetchJson("/api/client-config", "omit", signal);
    const configuration = await this.readJson<ClientConfiguration>(configResponse);
    if (!isClientConfiguration(configuration)) throw invalidApiResponse(configResponse.status);
    if (!this.isCurrent(attempt.generation)) throw createAbortError();
    if (this.snapshot.applicationId !== null && this.snapshot.applicationId !== configuration.applicationId) {
      this.advanceGeneration(attempt);
      await this.clearPrivateData();
      if (!this.isCurrent(attempt.generation)) throw createAbortError();
      if (attempt.announceChanges) this.signalAccountChange();
    }
    this.publish({ applicationId: configuration.applicationId });

    if (!configuration.accountsEnabled) {
      await this.publishSession(attempt, "disabled", disabledSession);
      return disabledSession;
    }

    const sessionResponse = await this.fetchJson("/api/auth/session", "same-origin", signal);
    const session = await this.readJson<Session>(sessionResponse);
    if (!isEnabledSession(session)) throw invalidApiResponse(sessionResponse.status);
    await this.publishSession(attempt, session.user ? "authenticated" : "anonymous", session);
    return session;
  }

  private async publishSession(attempt: SessionRefreshAttempt, status: "disabled" | "anonymous" | "authenticated", session: Session): Promise<void> {
    if (!this.isCurrent(attempt.generation)) throw createAbortError();
    const previousUserId = this.snapshot.session.user?.id ?? null;
    const nextUserId = session.user?.id ?? null;
    const hadSession = !this.snapshot.loading;
    if (previousUserId !== nextUserId) {
      this.advanceGeneration(attempt);
      await this.clearPrivateData();
      if (!this.isCurrent(attempt.generation)) throw createAbortError();
    }
    this.publish({ status, session, loading: false, checking: false, error: null });
    if (hadSession && previousUserId !== nextUserId && attempt.announceChanges) this.signalAccountChange();
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
    const accountMutation = isAccountMutationRequest(request);
    request.headers.set("Accept", "application/json");
    const path = new URL(request.url).pathname;
    const privateRequest = isPrivateRequest(path);
    const capturedOwner = request.headers.get("X-Expected-User") ?? this.snapshot.session.user?.id ?? null;

    if (privateRequest && capturedOwner !== null) {
      request.headers.set("X-Expected-User", capturedOwner);
    }

    if (request.method === "GET" || request.method === "HEAD") return request;

    const session = await this.refresh();
    if (privateRequest && capturedOwner !== (session.user?.id ?? null)) throw new AccountChangedError();
    if (request.signal.aborted || (!this.isCurrent(requestGeneration) && !accountMutation)) throw createAbortError();
    if (!session.enabled || !session.csrfToken) {
      throw new ApiError({ kind: "http", status: 503, message: "The account service is unavailable." });
    }
    request.headers.set("X-CSRF-TOKEN", session.csrfToken);
    return request;
  }

  private async sendApiRequest(request: Request): Promise<Response> {
    const requestGeneration = this.requestGenerations.get(request) ?? this.generation;
    const accountMutation = isAccountMutationRequest(request);
    if (request.signal.aborted || (!this.isCurrent(requestGeneration) && !accountMutation)) throw createAbortError();
    const response = await this.fetcher(request);
    if (request.signal.aborted || (!this.isCurrent(requestGeneration) && !accountMutation)) throw createAbortError();
    return response;
  }

  private guardApiMethod<TMethod extends (...args: never[]) => Promise<unknown>>(method: TMethod, isPost = false): TMethod {
    const invoke = method as unknown as (...args: unknown[]) => Promise<unknown>;
    const guarded = async (path: unknown, options?: RequestInit) => {
      const generation = this.generation;
      const controller = new AbortController();
      const accountMutation = isPost && isAccountMutationPath(path);
      const signal = options?.signal ? AbortSignal.any([controller.signal, options.signal]) : controller.signal;
      this.activeRequests.add(controller);
      if (accountMutation) this.accountMutationRequests.add(controller);
      try {
        // Keep cancellation and ownership checks around the entire typed operation,
        // including openapi-fetch's asynchronous response-body parsing.
        const result = await invoke(path, { ...options, signal });
        if (signal.aborted || (!this.isCurrent(generation) && !accountMutation)) throw createAbortError();
        return result;
      } catch (error) {
        if (error instanceof AccountChangedError) throw error;
        if (signal.aborted || (!this.isCurrent(generation) && !accountMutation)) throw createAbortError();
        throw error;
      } finally {
        this.activeRequests.delete(controller);
        this.accountMutationRequests.delete(controller);
      }
    };
    // Preserve openapi-fetch's path/init generics; only the optional signal changes.
    return guarded as unknown as TMethod;
  }

  private async handleApiResponse(request: Request, response: Response): Promise<void> {
    if ((response.status !== 401 && response.status !== 409) || !isPrivateRequest(new URL(request.url).pathname)) return;
    const code = await readProblemCode(response);
    if (!this.isCurrent(this.requestGenerations.get(request) ?? -1)) return;
    if (code === "SessionExpired" || code === "AuthenticationRequired" || code === "AccountChanged") {
      await this.changed().catch(() => {});
    }
  }

  private async clearPrivateData(): Promise<void> {
    await this.queryClient.cancelQueries({ queryKey: ["private"] });
    this.queryClient.removeQueries({ queryKey: ["private"] });
  }

  private signalAccountChange(): void {
    if (!this.disposed && this.snapshot.applicationId) this.onAccountChange?.(this.snapshot.applicationId);
  }

  private advanceGeneration(refreshAttempt?: { generation: number }, preserveAccountMutations = true): void {
    this.generation += 1;
    if (refreshAttempt) {
      // A refresh that discovers a different identity owns the new generation;
      // older API operations are cancelled without aborting that refresh itself.
      refreshAttempt.generation = this.generation;
      if (this.pendingRefresh) this.pendingRefresh.generation = this.generation;
    } else {
      this.refreshController?.abort();
      this.refreshController = undefined;
      this.pendingRefresh = undefined;
    }
    // Background refresh can observe an auth POST's cookie change before its response is consumed.
    for (const request of this.activeRequests) {
      if (preserveAccountMutations && this.accountMutationRequests.has(request)) continue;
      request.abort();
      this.activeRequests.delete(request);
    }
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

function isAccountMutationRequest(request: Request): boolean {
  return request.method === "POST" && isAccountMutationPath(new URL(request.url).pathname);
}

function isAccountMutationPath(path: unknown): boolean {
  return typeof path === "string" && path.startsWith("/api/auth/");
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
  return isJsonContentType(response.headers.get("content-type"));
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
