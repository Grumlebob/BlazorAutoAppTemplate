import { useEffect, useId, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { ApiError } from "../../api/errors";
import { apiResult, safeReturnPath } from "./account-api";
import { useAccounts } from "./account-context";
import { passwordPolicyError } from "./account-password-policy";
import { accountActionHasEmailRequirement, emailActionSubmitLabels, type AccountAction, type EmailAction } from "./account-form-model";

const inputClass = "mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 focus:border-indigo-600 focus:outline-2 focus:outline-indigo-600";
const buttonClass = "rounded-lg bg-indigo-700 px-5 py-2.5 font-medium text-white disabled:opacity-50";

export function SignInForm() {
  const accounts = useAccounts();
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const action = useSubmission();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const succeeded = await action.run(() => apiResult(accounts.api.POST("/api/auth/login", {
      body: { email, password, rememberMe },
    })), true);
    if (succeeded) navigate(safeReturnPath(search.get("returnTo")), { replace: true });
    setPassword("");
  }

  return <>
    <FormFeedback action={action} />
    <form className="mt-6 space-y-5" onSubmit={submit}>
      <label className="block font-medium">Email<input className={inputClass} type="email" name="email" autoComplete="email" maxLength={254} required {...fieldAttributes(action, "email")} value={email} onChange={event => setEmail(event.target.value)} /></label>
      <FieldError action={action} field="email" />
      <PasswordField label="Password" name="password" autoComplete="current-password" value={password} onChange={setPassword} error={fieldErrorMessage(action, "password")} required />
      <label className="flex items-center gap-2"><input type="checkbox" checked={rememberMe} onChange={event => setRememberMe(event.target.checked)} />Remember me on this device</label>
      <button className={buttonClass} disabled={action.pending || accounts.checking}>{action.pending ? "Please wait…" : "Sign in"}</button>
    </form>
    <div className="mt-6 flex flex-wrap gap-4 text-sm font-medium text-indigo-700">
      {accounts.session.registrationEnabled && <Link to="/auth/register">Create an account</Link>}
      {accounts.session.emailEnabled && <Link to="/auth/forgot-password">Forgot password?</Link>}
      {accounts.session.emailEnabled && <button disabled={action.pending || !email || accounts.checking} onClick={() => void action.run(() => apiResult(accounts.api.POST("/api/auth/resend-confirmation", { body: { email } })))}>Resend confirmation</button>}
    </div>
  </>;
}

export function RegistrationForm() {
  const accounts = useAccounts();
  const [email, setEmail] = useState("");
  const action = useSubmission();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await action.run(() => apiResult(accounts.api.POST("/api/auth/register", { body: { email } })));
  }

  return <>
    <FormFeedback action={action} />
    <form className="mt-6 space-y-5" onSubmit={submit}>
      <label className="block font-medium">Email<input className={inputClass} type="email" name="email" autoComplete="email" maxLength={254} required {...fieldAttributes(action, "email")} value={email} onChange={event => setEmail(event.target.value)} /></label>
      <FieldError action={action} field="email" />
      <p className="text-sm text-slate-600">Request received. Check your email if applicable; use resend if it does not arrive. Choose your password after confirming your email.</p>
      <button className={buttonClass} disabled={action.pending || accounts.checking}>{action.pending ? "Please wait…" : "Create an account"}</button>
    </form>
  </>;
}

export function EmailActionForm({ actionName }: { actionName: EmailAction }) {
  const accounts = useAccounts();
  const [email, setEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const action = useSubmission();
  const tokens = useFragmentTokens();
  const tokenAction = actionName !== "forgot-password";
  const missingTokens = !tokens.userId || !tokens.token || (actionName === "confirm-email-change" && !tokens.email);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (actionName === "forgot-password") {
      await action.run(() => apiResult(accounts.api.POST("/api/auth/forgot-password", { body: { email } })));
    } else if (actionName === "reset-password") {
      await action.run(() => apiResult(accounts.api.POST("/api/auth/reset-password", { body: { ...tokens, newPassword } })), true);
    } else if (actionName === "confirm-email") {
      await action.run(() => apiResult(accounts.api.POST("/api/auth/confirm-email", {
        body: { userId: tokens.userId, token: tokens.token, newPassword },
      })));
    } else {
      await action.run(() => apiResult(accounts.api.POST("/api/auth/confirm-email-change", { body: tokens })), true);
    }
    setNewPassword("");
  }

  return <>
    <FormFeedback action={action} />
    <form className="mt-6 space-y-5" onSubmit={submit}>
      {actionName === "forgot-password" && <><label className="block font-medium">Email<input className={inputClass} type="email" name="email" autoComplete="email" maxLength={254} required {...fieldAttributes(action, "email")} value={email} onChange={event => setEmail(event.target.value)} /></label><FieldError action={action} field="email" /></>}
      {(actionName === "reset-password" || actionName === "confirm-email") && <PasswordField label={actionName === "confirm-email" ? "Choose password" : "New password"} name="newPassword" autoComplete="new-password" value={newPassword} onChange={setNewPassword} error={fieldErrorMessage(action, "newPassword")} required passwordPolicy />}
      {tokenAction && missingTokens ? <p role="alert">This link is incomplete. Request a new email and open its full link.</p> : <button className={buttonClass} disabled={action.pending || accounts.checking}>{action.pending ? "Please wait…" : emailActionSubmitLabels[actionName]}</button>}
    </form>
  </>;
}

export function AccountSettingsForm() {
  const accounts = useAccounts();
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [email, setEmail] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const action = useSubmission();

  async function downloadData() {
    const data = await apiResult(accounts.api.POST("/api/auth/export", { body: { password } }));
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "account-data.json";
    link.click();
    URL.revokeObjectURL(url);
    setPassword("");
    return { message: "Account data exported." };
  }

  return <>
    {accounts.checking && <p className="mt-4" role="status">Checking your session…</p>}
    <div hidden={accounts.checking}>
      <p className="mt-3 text-slate-600">{accounts.session.user?.email}</p>
      {accounts.session.user?.roles?.includes("Admin") && <p className="mt-2 text-sm font-medium text-indigo-800">Admin</p>}
      <p className="mt-5 text-sm text-slate-600">Enter your current password to change account details, export data or sign out all sessions.</p>
      <FormFeedback action={action} />
      <div className="mt-4"><PasswordField label="Current password" name="password" autoComplete="current-password" value={password} onChange={setPassword} error={fieldErrorMessage(action, "password")} /></div>
      <form className="mt-6 space-y-4 border-t border-slate-200 pt-6" onSubmit={async event => {
        event.preventDefault();
        await action.run(() => apiResult(accounts.api.POST("/api/auth/change-password", { body: { password, newPassword } })), true);
        setPassword(""); setNewPassword("");
      }}>
        <h2 className="text-xl font-semibold">Change password</h2>
        <PasswordField label="New password" name="newPassword" autoComplete="new-password" value={newPassword} onChange={setNewPassword} error={fieldErrorMessage(action, "newPassword")} required passwordPolicy />
        <button className={buttonClass} disabled={action.pending || accounts.checking || !password}>Change password</button>
      </form>
      {accounts.session.emailEnabled && <form className="mt-6 space-y-4 border-t border-slate-200 pt-6" onSubmit={async event => {
        event.preventDefault(); await action.run(() => apiResult(accounts.api.POST("/api/auth/change-email", { body: { password, email } }))); setPassword("");
      }}>
        <h2 className="text-xl font-semibold">Change email</h2>
        <label className="block font-medium">New email<input className={inputClass} type="email" autoComplete="email" maxLength={254} required {...fieldAttributes(action, "email")} value={email} onChange={event => setEmail(event.target.value)} /></label>
        <FieldError action={action} field="email" />
        <button className={buttonClass} disabled={action.pending || accounts.checking || !password}>Send confirmation</button>
      </form>}
      <div className="mt-6 flex flex-wrap gap-3 border-t border-slate-200 pt-6">
        <button className={buttonClass} disabled={action.pending || accounts.checking} onClick={() => void action.run(() => apiResult(accounts.api.POST("/api/auth/logout")), true)}>Sign out</button>
        <button className={buttonClass} disabled={action.pending || accounts.checking || !password} onClick={() => void action.run(() => apiResult(accounts.api.POST("/api/auth/logout-all", { body: { password } })), true)}>Sign out all sessions</button>
        <button className={buttonClass} disabled={action.pending || accounts.checking || !password} onClick={() => void action.run(downloadData)}>Export my data</button>
      </div>
      <div className="mt-8 rounded-lg border border-red-200 bg-red-50 p-5">
        <h2 className="font-semibold text-red-950">Delete account</h2>
        <p className="mt-2 text-sm text-red-900">This permanently deletes your account and private books. This cannot be undone.</p>
        <label className="mt-4 flex gap-2"><input type="checkbox" checked={confirmDelete} onChange={event => setConfirmDelete(event.target.checked)} />I understand and want to delete my account.</label>
        <button className="mt-4 rounded-lg bg-red-800 px-4 py-2 text-white disabled:opacity-50" disabled={action.pending || accounts.checking || !password || !confirmDelete} onClick={() => void action.run(() => apiResult(accounts.api.POST("/api/auth/delete", { body: { password } })), true)}>Delete my account</button>
      </div>
    </div>
  </>;
}

function useSubmission() {
  const accounts = useAccounts();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<ApiError["fieldErrors"]>();
  const feedbackId = useId();

  async function run(operation: () => Promise<{ message?: string | null }>, sessionChanges = false): Promise<boolean> {
    setPending(true); setError(""); setMessage(""); setFieldErrors(undefined);
    try {
      const result = await operation();
      if (sessionChanges) await accounts.changed();
      setMessage(result.message ?? "Done.");
      return true;
    } catch (failure) {
      if (failure instanceof ApiError) setFieldErrors(failure.fieldErrors);
      setError(failure instanceof ApiError && failure.kind === "network"
        ? "The account service is unavailable. Try again."
        : failure instanceof Error ? failure.message : "The request failed. Please try again.");
      return false;
    } finally {
      setPending(false);
    }
  }

  return { pending, message, error, fieldErrors, feedbackId, run };
}

function fieldErrorMessage(action: ReturnType<typeof useSubmission>, field: string) {
  return Object.entries(action.fieldErrors ?? {})
    .find(([key]) => key.toLowerCase() === field.toLowerCase())?.[1].join(" ");
}

function fieldAttributes(action: ReturnType<typeof useSubmission>, field: string) {
  const invalid = !!fieldErrorMessage(action, field);
  return { "aria-invalid": invalid || undefined, "aria-describedby": invalid ? `${action.feedbackId}-${field}` : undefined };
}

function FieldError({ action, field }: { action: ReturnType<typeof useSubmission>; field: string }) {
  const message = fieldErrorMessage(action, field);
  return message ? <p className="mt-2 text-sm text-red-800" id={`${action.feedbackId}-${field}`}>{message}</p> : null;
}

function FormFeedback({ action }: { action: ReturnType<typeof useSubmission> }) {
  return <>
    {action.message && <p className="mt-5 rounded-lg bg-emerald-50 p-4 text-emerald-900" role="status">{action.message}</p>}
    {action.error && <p className="mt-5 rounded-lg bg-red-50 p-4 text-red-900" role="alert">{action.error}</p>}
  </>;
}

export function PasswordField({
  label,
  name,
  autoComplete,
  value,
  onChange,
  error,
  required = false,
  passwordPolicy = false,
}: {
  label: string;
  name: string;
  autoComplete: "current-password" | "new-password";
  value: string;
  onChange: (value: string) => void;
  error?: string;
  required?: boolean;
  passwordPolicy?: boolean;
}) {
  const id = useId();
  const policyId = `${id}-policy`;
  const errorId = `${id}-error`;
  const [visible, setVisible] = useState(false);

  return <div>
    <label className="block font-medium" htmlFor={id}>{label}</label>
    <div className="mt-2 flex rounded-lg border border-slate-300 bg-white focus-within:border-indigo-600 focus-within:outline-2 focus-within:outline-indigo-600">
      <input
        className="min-w-0 flex-1 rounded-l-lg bg-transparent px-3 py-2.5 focus:outline-none"
        id={id}
        type={visible ? "text" : "password"}
        name={name}
        autoComplete={autoComplete}
        maxLength={256}
        required={required}
        value={value}
        aria-invalid={!!error || undefined}
        aria-describedby={[passwordPolicy ? policyId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined}
        onChange={event => {
          const nextValue = event.target.value;
          onChange(nextValue);
          event.target.setCustomValidity(passwordPolicy ? passwordPolicyError(nextValue) : "");
        }}
      />
      <button className="rounded-r-lg px-3 text-sm font-medium text-indigo-700" type="button" aria-label={`${visible ? "Hide" : "Show"} ${label.toLowerCase()}`} aria-pressed={visible} onClick={() => setVisible(current => !current)}>
        {visible ? "Hide" : "Show"}
      </button>
    </div>
    {passwordPolicy && <p className="mt-2 text-sm text-slate-600" id={policyId}>Use 15–128 Unicode characters. Avoid common or app-related passwords.</p>}
    {error && <p className="mt-2 text-sm text-red-800" id={errorId}>{error}</p>}
  </div>;
}

function useFragmentTokens() {
  const [tokens] = useState(() => {
    const values = new URLSearchParams(typeof window === "undefined" ? "" : window.location.hash.slice(1));
    return { userId: values.get("userId") ?? "", token: values.get("token") ?? "", email: values.get("email") ?? "" };
  });
  useEffect(() => {
    if (typeof window !== "undefined" && window.location.hash) {
      window.history.replaceState(window.history.state, "", window.location.pathname + window.location.search);
    }
  });
  return tokens;
}

export function AccountActionForm({ action }: { action: AccountAction }) {
  if (action === "login") return <SignInForm />;
  if (action === "register") return <RegistrationForm />;
  if (action === "settings") return <AccountSettingsForm />;
  if (accountActionHasEmailRequirement(action)) {
    return <EmailActionForm actionName={action} />;
  }
  return null;
}
