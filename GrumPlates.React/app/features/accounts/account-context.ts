import { createContext, useContext } from "react";
import type { ApiClient } from "../../api/api-client";
import type { Session } from "./account-api";
import type { AccountStatus } from "./account-session-controller";

export interface AccountState {
  status: AccountStatus;
  session: Session;
  loading: boolean;
  checking: boolean;
  error: string | null;
  applicationId: string | null;
  api: ApiClient;
  refresh: () => Promise<Session>;
  changed: () => Promise<Session>;
}

export const AccountContext = createContext<AccountState | null>(null);
export function useAccounts() {
  const state = useContext(AccountContext);
  if (!state) throw new Error("AccountProvider is required.");
  return state;
}
