import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { PasswordField } from "./account-form-parts";
import { passwordPolicyError } from "./account-password-policy";

afterEach(cleanup);

describe("account password field", () => {
  it.each([
    ["14 ASCII characters", "x".repeat(14), false],
    ["15 ASCII characters", "x".repeat(15), true],
    ["128 non-BMP characters", "😀".repeat(128), true],
    ["129 non-BMP characters", "😀".repeat(129), false],
  ])("validates %s against the shared new-password policy", (_caseName, value, valid) => {
    render(<PasswordField label="New password" name="newPassword" autoComplete="new-password" value="" onChange={() => undefined} passwordPolicy />);
    const input = screen.getByLabelText<HTMLInputElement>("New password");
    fireEvent.change(input, { target: { value } });
    expect(input.validity.valid).toBe(valid);
  });

  it("rejects control characters and malformed UTF-16 values", () => {
    expect(passwordPolicyError(`${"x".repeat(15)}\n`)).not.toBe("");
    expect(passwordPolicyError(`${"x".repeat(15)}\uD800`)).not.toBe("");
  });

  it("allows short existing credentials and can reveal and hide the value", async () => {
    const user = userEvent.setup();
    render(<PasswordField label="Current password" name="password" autoComplete="current-password" value="" onChange={() => undefined} />);
    const input = screen.getByLabelText<HTMLInputElement>("Current password");
    fireEvent.change(input, { target: { value: "legacy" } });
    expect(input.validity.valid).toBe(true);
    expect(input).toHaveAttribute("maxLength", "256");
    expect(input).toHaveAttribute("autocomplete", "current-password");

    await user.click(screen.getByRole("button", { name: "Show current password" }));
    expect(input).toHaveAttribute("type", "text");
    await user.click(screen.getByRole("button", { name: "Hide current password" }));
    expect(input).toHaveAttribute("type", "password");
  });
});
