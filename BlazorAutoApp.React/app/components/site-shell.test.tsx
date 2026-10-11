import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { SiteShell } from "./site-shell";

describe("public site shell", () => {
  it("provides keyboard-accessible navigation and no account controls", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={["/books"]}>
        <SiteShell>
          <h1 id="page-title">Book catalog</h1>
        </SiteShell>
      </MemoryRouter>,
    );

    const skipLink = screen.getByRole("link", { name: "Skip to content" });
    expect(skipLink).toHaveAttribute("href", "#main-content");
    expect(skipLink).toHaveClass("focus:not-sr-only");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(screen.getByRole("main")).toHaveAttribute("aria-labelledby", "page-title");
    expect(screen.getByRole("navigation", { name: "Main navigation" })).toBeInTheDocument();
    const booksLink = screen.getByRole("link", { name: "Books" });
    expect(booksLink).toHaveAttribute("href", "/books");
    expect(booksLink).toHaveAttribute("aria-current", "page");
    expect(booksLink).toHaveClass("focus-visible:outline-2");
    await user.tab();
    expect(skipLink).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("link", { name: "The Authors Bookcase home" })).toHaveFocus();
    await user.click(skipLink);
    expect(screen.getByRole("main")).toHaveFocus();
    expect(screen.queryByRole("link", { name: /log in|sign in|account/i })).not.toBeInTheDocument();
  });
});
