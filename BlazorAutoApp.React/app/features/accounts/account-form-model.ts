export const accountActionTitles: Record<string, string> = {
  login: "Sign in",
  register: "Create an account",
  "forgot-password": "Reset your password",
  "reset-password": "Choose a new password",
  "confirm-email": "Confirm your email",
  "confirm-email-change": "Confirm your new email",
  settings: "Your account",
};

export function accountActionHasEmailRequirement(action: string): boolean {
  return ["forgot-password", "reset-password", "confirm-email", "confirm-email-change"].includes(action);
}
