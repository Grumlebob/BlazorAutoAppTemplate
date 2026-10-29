import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createApiClient } from "../../api/api-client";
import { AccountContext, type AccountState } from "./account-context";
import type { Session } from "./account-api";
import { EmailActionForm, RegistrationForm } from "./account-form-parts";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.history.replaceState(window.history.state, "", "/");
});

describe("account forms", () => {
  it("announces accepted registration with a status role", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ message: "Request received. Check your email if applicable; use resend if it does not arrive." }), {
      status: 202,
      headers: { "content-type": "application/json" },
    }));
    const user = userEvent.setup();
    renderWithAccount(<RegistrationForm />, fetcher);

    await user.type(screen.getByRole("textbox", { name: "Email" }), "reader@example.test");
    await user.click(screen.getByRole("button", { name: "Create an account" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Request received. Check your email if applicable");
    expect(fetcher).toHaveBeenCalledOnce();
  });

  it("announces safe account-service failures without exposing thrown network details", async () => {
    const fetcher = vi.fn(async () => { throw new TypeError("Failed to fetch internal-auth-host"); });
    const user = userEvent.setup();
    renderWithAccount(<RegistrationForm />, fetcher);

    await user.type(screen.getByRole("textbox", { name: "Email" }), "reader@example.test");
    await user.click(screen.getByRole("button", { name: "Create an account" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The account service is unavailable. Try again.");
    expect(alert).not.toHaveTextContent("internal-auth-host");
  });

  it("cleans proof fragments and identifies an email-change link missing its target", async () => {
    window.history.replaceState(window.history.state, "", "/auth/confirm-email#userId=user-1&token=proof-token");
    const view = renderWithAccount(<EmailActionForm actionName="confirm-email" />, async () => new Response(null, { status: 204 }));

    await waitFor(() => expect(window.location.hash).toBe(""));
    const password = screen.getByLabelText<HTMLInputElement>("Choose password");
    const helpId = password.getAttribute("aria-describedby");
    expect(helpId).toBeTruthy();
    expect(document.getElementById(helpId!)).toHaveTextContent("Use 15–128 Unicode characters");
    view.unmount();

    window.history.replaceState(window.history.state, "", "/auth/confirm-email-change#userId=user-1&token=proof-token");
    renderWithAccount(<EmailActionForm actionName="confirm-email-change" />, async () => new Response(null, { status: 204 }));

    expect(screen.getByRole("alert")).toHaveTextContent("This link is incomplete.");
    expect(screen.queryByRole("button", { name: "Confirm new email" })).not.toBeInTheDocument();
  });

  it("associates server email validation with the email field", async () => {
    const user = userEvent.setup();
    renderWithAccount(<RegistrationForm />, async () => validationProblem("email", "Enter a valid email address."));
    const email = screen.getByRole("textbox", { name: "Email" });
    await user.type(email, "reader@example.test");
    await user.click(screen.getByRole("button", { name: "Create an account" }));

    await screen.findByRole("alert");
    expect(email).toHaveAttribute("aria-invalid", "true");
    expect(email).toHaveAccessibleDescription("Enter a valid email address.");
  });

  it("associates rejected server password policy with the password field and retains policy help", async () => {
    window.history.replaceState(window.history.state, "", "/auth/confirm-email#userId=user-1&token=proof-token");
    const user = userEvent.setup();
    renderWithAccount(<EmailActionForm actionName="confirm-email" />, async () => validationProblem("newPassword", "Choose a password unrelated to your email."));
    const password = screen.getByLabelText("Choose password");
    await user.type(password, "reader@example.test");
    await user.click(screen.getByRole("button", { name: "Confirm email and create account" }));

    await screen.findByRole("alert");
    expect(password).toHaveAttribute("aria-invalid", "true");
    expect(password).toHaveAccessibleDescription(/Use 15–128 Unicode characters.*Choose a password unrelated to your email\./);
  });
});

function validationProblem(field: string, message: string) {
  return new Response(JSON.stringify({ title: "Validation failed", detail: "Check the highlighted field.", errors: { [field]: [message] } }), {
    status: 400, headers: { "content-type": "application/problem+json" },
  });
}

function renderWithAccount(
  children: React.ReactNode,
  fetcher: (request: Request) => Promise<Response>,
) {
  const session: Session = {
    enabled: true,
    registrationEnabled: true,
    emailEnabled: true,
    csrfToken: "test-csrf",
    user: null,
  };
  const value: AccountState = {
    status: "anonymous",
    session,
    loading: false,
    checking: false,
    error: null,
    applicationId: "a".repeat(32),
    api: createApiClient({ baseUrl: "https://app.example.test", credentials: "same-origin", fetch: fetcher }),
    refresh: async () => session,
    changed: async () => session,
  };
  return render(<AccountContext.Provider value={value}>{children}</AccountContext.Provider>);
}
