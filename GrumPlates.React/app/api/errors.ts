import type { components } from "./generated/schema";

export type ApiErrorKind = "http" | "network" | "invalid-response";
export type ProblemDetails = components["schemas"]["ProblemDetails"];
export type HttpValidationProblemDetails = components["schemas"]["HttpValidationProblemDetails"];

export interface ApiErrorOptions {
  kind: ApiErrorKind;
  message: string;
  status?: number;
  title?: string;
  detail?: string;
  fieldErrors?: Readonly<Record<string, readonly string[]>>;
  retryAfterMs?: number;
  correlationId?: string;
  cause?: unknown;
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status?: number;
  readonly title?: string;
  readonly detail?: string;
  readonly fieldErrors?: Readonly<Record<string, readonly string[]>>;
  readonly retryAfterMs?: number;
  readonly correlationId?: string;

  constructor(options: ApiErrorOptions) {
    super(options.message, { cause: options.cause });
    this.name = "ApiError";
    this.kind = options.kind;
    this.status = options.status;
    this.title = options.title;
    this.detail = options.detail;
    this.fieldErrors = options.fieldErrors;
    this.retryAfterMs = options.retryAfterMs;
    this.correlationId = options.correlationId;
  }
}

const maximumRetryAfterMs = 60_000;
const maximumFieldCount = 20;
const maximumMessagesPerField = 10;
const maximumTextLength = 300;

export function toHttpApiError(response: Response, body: unknown, now = Date.now()): ApiError {
  const problem = isJsonContentType(response.headers.get("content-type")) ? asProblemDetails(body) : undefined;
  const title = safeText(problem?.title);
  const detail = safeText(problem?.detail);
  const message = detail ?? title ?? `The request failed (HTTP ${response.status}).`;

  return new ApiError({
    kind: "http",
    message,
    status: response.status,
    title,
    detail,
    fieldErrors: normalizeFieldErrors(problem?.errors),
    retryAfterMs: parseRetryAfter(response.headers.get("retry-after"), now),
    correlationId: getCorrelationId(response),
  });
}

export function invalidApiResponse(status: number, cause?: unknown): ApiError {
  return new ApiError({
    kind: "invalid-response",
    message: "The service returned an invalid response.",
    status,
    cause,
  });
}

export function normalizeTransportError(error: unknown): Error {
  if (isAbortError(error)) {
    return error;
  }

  if (error instanceof ApiError) {
    return error;
  }

  if (error instanceof TypeError) {
    return new ApiError({
      kind: "network",
      message: "The catalog service is unavailable.",
      cause: error,
    });
  }

  return error instanceof Error
    ? error
    : new ApiError({ kind: "network", message: "The catalog service is unavailable.", cause: error });
}

export function isAbortError(error: unknown): error is Error {
  return typeof error === "object" && error !== null && "name" in error && error.name === "AbortError";
}

export function isJsonContentType(contentType: string | null): boolean {
  if (!contentType) {
    return false;
  }

  const mediaType = contentType.split(";", 1)[0]?.trim().toLowerCase();
  return mediaType === "application/json" || (mediaType?.startsWith("application/") === true && mediaType.endsWith("+json"));
}

export function isJsonSuccessContentType(contentType: string | null): boolean {
  return contentType?.split(";", 1)[0]?.trim().toLowerCase() === "application/json";
}

export function parseRetryAfter(value: string | null, now = Date.now()): number | undefined {
  if (!value) {
    return undefined;
  }

  const trimmed = value.trim();
  if (/^\d+$/.test(trimmed)) {
    return Math.min(Number(trimmed) * 1_000, maximumRetryAfterMs);
  }

  const timestamp = Date.parse(trimmed);
  if (!Number.isFinite(timestamp)) {
    return undefined;
  }

  return Math.min(Math.max(timestamp - now, 0), maximumRetryAfterMs);
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return undefined;
  }

  return value as Record<string, unknown>;
}

function asProblemDetails(value: unknown): Partial<ProblemDetails & HttpValidationProblemDetails> | undefined {
  if (!asRecord(value)) {
    return undefined;
  }

  return value as Partial<ProblemDetails & HttpValidationProblemDetails>;
}

function safeText(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }

  const normalized = Array.from(value, (character) => (isControlCharacter(character) ? " " : character)).join("").trim();
  if (normalized.length === 0 || normalized.length > maximumTextLength || /[<>]/.test(normalized)) {
    return undefined;
  }

  return normalized;
}

function normalizeFieldErrors(value: unknown): Readonly<Record<string, readonly string[]>> | undefined {
  const errors = asRecord(value);
  if (!errors) {
    return undefined;
  }

  const normalized = Object.entries(errors)
    .slice(0, maximumFieldCount)
    .map(([field, messages]) => {
      const safeField = safeText(field);
      if (!safeField || !Array.isArray(messages)) {
        return undefined;
      }

      const safeMessages = messages
        .slice(0, maximumMessagesPerField)
        .map(safeText)
        .filter((message): message is string => message !== undefined);

      return safeMessages.length > 0 ? [safeField, safeMessages] as const : undefined;
    })
    .filter((entry): entry is readonly [string, string[]] => entry !== undefined);

  return normalized.length > 0 ? Object.fromEntries(normalized) : undefined;
}

function getCorrelationId(response: Response): string | undefined {
  for (const header of ["x-correlation-id", "x-request-id", "request-id", "traceparent"]) {
    const value = response.headers.get(header)?.trim();
    if (value && value.length <= 200 && !hasControlCharacters(value) && !/[<>]/.test(value)) {
      return value;
    }
  }

  return undefined;
}

function isControlCharacter(value: string): boolean {
  const code = value.charCodeAt(0);
  return code < 32 || code === 127;
}

function hasControlCharacters(value: string): boolean {
  return Array.from(value).some(isControlCharacter);
}
