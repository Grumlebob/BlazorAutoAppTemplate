import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { RouteErrorPage } from "./route-error-page";

describe("safe route errors", () => {
  it("shows a useful not-found page without exposing internal error details", () => {
    render(
      <MemoryRouter>
        <RouteErrorPage notFound />
      </MemoryRouter>,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "This page couldn't be found." })).toHaveAttribute("id", "page-title");
    expect(screen.getByRole("link", { name: "Browse the books" })).toHaveAttribute("href", "/books");
    expect(screen.queryByText(/stack trace|internal server|exception/i)).not.toBeInTheDocument();
  });

  it("shows a generic recovery page for unexpected failures", () => {
    render(
      <MemoryRouter>
        <RouteErrorPage notFound={false} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "We couldn't load this page." })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Return home" })).toHaveAttribute("href", "/");
  });
});
