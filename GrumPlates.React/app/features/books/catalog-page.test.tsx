import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import type { components } from "../../api/generated/schema";
import { publicApi } from "../../api/client";
import { ApiError } from "../../api/errors";
import { afterEach, describe, expect, it, vi } from "vitest";
import { CatalogPage } from "./catalog-page";

const sampleBook = {
  id: 12,
  seedKey: "ship",
  title: "Ship Inspections",
  author: "Jacob Grum",
  url: null,
} satisfies components["schemas"]["AuthorBookListItemResponse"];

function renderCatalog() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/books"]}>
        <CatalogPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("public catalog", () => {
  it("shows generated public book data and a stable author-detail URL", async () => {
    vi.spyOn(publicApi, "listAuthorBooks").mockResolvedValue({ books: [sampleBook] });

    renderCatalog();

    expect(await screen.findByRole("heading", { name: "Ship Inspections" })).toBeInTheDocument();
    expect(screen.getByText("By Jacob Grum")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ship Inspections" })).toHaveAttribute("href", "/books/author/ship");
    expect(screen.getByRole("region", { name: "Public book listings" }).querySelector(".grid")).toHaveClass("grid-cols-1", "sm:grid-cols-2", "lg:grid-cols-3");
  });

  it("announces loading while the catalog request is pending", async () => {
    let resolveList: (value: components["schemas"]["GetAuthorBooksResponse"]) => void = () => {};
    vi.spyOn(publicApi, "listAuthorBooks").mockImplementation(
      () => new Promise((resolve) => {
        resolveList = resolve;
      }),
    );

    renderCatalog();

    expect(screen.getByRole("status")).toHaveTextContent("Loading the public catalog");
    await act(async () => resolveList({ books: [] }));
    expect(await screen.findByRole("heading", { name: "The shelf is quiet for now." })).toBeInTheDocument();
  });

  it("shows an empty state when the public catalog has no entries", async () => {
    vi.spyOn(publicApi, "listAuthorBooks").mockResolvedValue({ books: [] });

    renderCatalog();

    expect(await screen.findByRole("heading", { name: "The shelf is quiet for now." })).toBeInTheDocument();
  });

  it("shows bounded rate-limit guidance and allows an explicit retry", async () => {
    const listBooks = vi.spyOn(publicApi, "listAuthorBooks")
      .mockRejectedValueOnce(new ApiError({ kind: "http", status: 429, retryAfterMs: 5_000, message: "Rate limited" }))
      .mockResolvedValueOnce({ books: [sampleBook] });

    renderCatalog();

    expect(await screen.findByRole("heading", { name: "The catalog is busy." })).toBeInTheDocument();
    expect(screen.getByText("You can try again in about 5 seconds.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Ship Inspections" })).toBeInTheDocument();
    expect(listBooks).toHaveBeenCalledTimes(2);
  });

  it("shows a safe network-failure state", async () => {
    vi.spyOn(publicApi, "listAuthorBooks").mockRejectedValue(new ApiError({ kind: "network", message: "secret network detail" }));

    renderCatalog();

    expect(await screen.findByRole("heading", { name: "The catalog is out of reach." })).toBeInTheDocument();
    expect(screen.queryByText("secret network detail")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("shows a safe server-error state", async () => {
    vi.spyOn(publicApi, "listAuthorBooks").mockRejectedValue(new ApiError({ kind: "http", status: 503, message: "Private upstream detail" }));

    renderCatalog();

    expect(await screen.findByRole("heading", { name: "The catalog is taking a break." })).toBeInTheDocument();
    expect(screen.queryByText("Private upstream detail")).not.toBeInTheDocument();
  });

  it("shows an invalid-response state without raw response content", async () => {
    vi.spyOn(publicApi, "listAuthorBooks").mockRejectedValue(new ApiError({ kind: "invalid-response", status: 200, message: "<html>upstream</html>" }));

    renderCatalog();

    expect(await screen.findByRole("heading", { name: "We couldn't read the catalog." })).toBeInTheDocument();
    expect(screen.queryByText("<html>upstream</html>")).not.toBeInTheDocument();
  });
});
