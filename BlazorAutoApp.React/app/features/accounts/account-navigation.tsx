import { Link } from "react-router";
import { useContext } from "react";
import { AccountContext } from "./account-context";

export function AccountNavigation() {
  const state = useContext(AccountContext);
  if (!state) return null;
  const { session, loading, checking, status } = state;
  if (loading || checking || (status !== "anonymous" && status !== "authenticated")) return null;
  return session.user ? <>
    <Link className="rounded-full px-4 py-2 text-sm font-medium hover:bg-slate-100" to="/my-books">My books</Link>
    <Link className="rounded-full px-4 py-2 text-sm font-medium hover:bg-slate-100" to="/auth/settings">Account</Link>
  </> : <Link className="rounded-full bg-indigo-700 px-4 py-2 text-sm font-medium text-white" to="/auth/login">Sign in</Link>;
}
