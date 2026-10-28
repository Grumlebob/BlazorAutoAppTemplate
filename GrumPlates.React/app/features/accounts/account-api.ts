import type { components } from "../../api/generated/schema";
import { ApiError } from "../../api/errors";

export type Session = components["schemas"]["AccountSession"];
export type ClientConfiguration = components["schemas"]["ClientConfiguration"];

export const disabledSession: Session = {
  enabled: false,
  registrationEnabled: false,
  emailEnabled: false,
  csrfToken: "",
  user: null,
};

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
