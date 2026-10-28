import { Link, useLocation, useParams } from "react-router";
import { useAccounts } from "../features/accounts/account-context";
import { AccountActionForm } from "../features/accounts/account-form-parts";
import { accountActionHasEmailRequirement, accountActionTitles, isAccountAction } from "../features/accounts/account-form-model";

export function meta() { return [{ title: "Account | The Authors Bookcase" }]; }

export default function AccountPage() {
  const { action = "login" } = useParams();
  const location = useLocation();
  return <AccountRoute key={location.pathname} action={action} />;
}

function AccountRoute({ action }: { action: string }) {
  const accounts = useAccounts();
  if (!isAccountAction(action)) return <section><h1 id="page-title">Page not found</h1><Link to="/">Return home</Link></section>;
  const title = accountActionTitles[action];
  if (accounts.loading) return <p role="status">Loading account…</p>;
  if (accounts.status === "unavailable") {
    return <section className="mx-auto max-w-lg"><h1 className="text-3xl font-semibold" id="page-title">Account service unavailable</h1><p className="mt-4">{accounts.error ?? "The account service could not be reached."}</p><button className="mt-6 text-indigo-700 disabled:opacity-50" disabled={accounts.checking} onClick={() => void accounts.refresh().catch(() => {})}>{accounts.checking ? "Checking your session…" : "Try again"}</button><Link className="ml-6 mt-6 inline-block text-indigo-700" to="/">Return home</Link></section>;
  }
  if (accounts.status === "disabled") {
    return <section className="mx-auto max-w-lg"><h1 className="text-3xl font-semibold" id="page-title">Accounts are unavailable</h1><p className="mt-4">This site currently provides its public catalog only.</p><Link className="mt-6 inline-block text-indigo-700" to="/">Return home</Link></section>;
  }

  const authenticated = accounts.status === "authenticated";
  const unavailable = (action === "register" && !accounts.session.registrationEnabled)
    || (accountActionHasEmailRequirement(action) && !accounts.session.emailEnabled);

  return <section className="mx-auto max-w-lg">
    <h1 className="text-3xl font-semibold tracking-tight" id="page-title">{title}</h1>
    {accounts.error && <p className="mt-5 rounded-lg bg-red-50 p-4 text-red-900" role="alert">{accounts.error}</p>}
    {unavailable ? <p className="mt-5">This account operation is not enabled on this site.</p>
      : action === "settings" && !authenticated ? <p className="mt-5">Sign in to manage your account. <Link className="text-indigo-700" to="/auth/login?returnTo=/auth/settings">Sign in</Link></p>
        : <div className="mt-4"><AccountActionForm key={`${accounts.applicationId}:${accounts.session.user?.id ?? "anonymous"}`} action={action} /></div>}
    <div className="mt-6 flex flex-wrap gap-4 text-sm font-medium text-indigo-700">
      {action !== "login" && <Link to="/auth/login">Sign in</Link>}
      {action === "login" && accounts.session.registrationEnabled && <Link to="/auth/register">Create an account</Link>}
      {action === "login" && accounts.session.emailEnabled && <Link to="/auth/forgot-password">Forgot password?</Link>}
      {authenticated && <Link to="/my-books">My books</Link>}
    </div>
  </section>;
}
