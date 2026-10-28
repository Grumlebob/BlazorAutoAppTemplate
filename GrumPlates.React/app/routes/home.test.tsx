import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import Home from "./home";

describe("home route", () => {
  it("introduces the public collection and links to the catalog without account controls", () => {
    render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Find a book that stays with you." })).toHaveAttribute("id", "page-title");
    expect(screen.getByRole("link", { name: "Browse the books" })).toHaveAttribute("href", "/books");
    expect(screen.queryByRole("link", { name: /log in|sign in|account/i })).not.toBeInTheDocument();
  });
});
