import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, Outlet, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "./root";

function RouteOutlet() {
  return <Outlet />;
}

function BrokenPage(): never {
  throw new Error("Sensitive database connection detail");
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("root route error boundary", () => {
  it("hides unexpected exception details", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const router = createMemoryRouter(
      [{ Component: RouteOutlet, ErrorBoundary, children: [{ Component: BrokenPage, index: true }] }],
      { initialEntries: ["/"] },
    );
    const view = render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "We couldn't load this page." })).toBeInTheDocument();
    expect(screen.queryByText(/Sensitive database connection detail/)).not.toBeInTheDocument();
    await waitFor(() => expect(document.title).toBe("We couldn't load this page | The Authors Bookcase"));

    view.unmount();
    router.dispose();
  });

  it("presents unmatched paths as a safe not-found page", async () => {
    const router = createMemoryRouter(
      [{ Component: RouteOutlet, ErrorBoundary, children: [{ Component: () => <p>Catalog</p>, path: "books" }] }],
      { initialEntries: ["/missing-page"] },
    );
    const view = render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "This page couldn't be found." })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Browse the books" })).toHaveAttribute("href", "/books");
    await waitFor(() => expect(document.title).toBe("Page not found | The Authors Bookcase"));

    view.unmount();
    router.dispose();
  });
});
