export const accountActionTitles = {
  login: "Sign in",
  register: "Create an account",
  "forgot-password": "Reset your password",
  "reset-password": "Choose a new password",
  "confirm-email": "Confirm your email",
  "confirm-email-change": "Confirm your new email",
  settings: "Your account",
} as const;

export type AccountAction = keyof typeof accountActionTitles;

export const emailActionSubmitLabels = {
  "forgot-password": "Send reset link",
  "reset-password": "Choose a new password",
  "confirm-email": "Confirm email and create account",
  "confirm-email-change": "Confirm new email",
} as const;

export type EmailAction = keyof typeof emailActionSubmitLabels;

export function isAccountAction(action: string): action is AccountAction {
  return Object.hasOwn(accountActionTitles, action);
}

export function accountActionHasEmailRequirement(action: string): action is EmailAction {
  return Object.hasOwn(emailActionSubmitLabels, action);
}
