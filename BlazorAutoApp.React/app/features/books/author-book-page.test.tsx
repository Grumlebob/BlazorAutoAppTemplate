import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import type { components } from "../../api/generated/schema";
import { publicApi } from "../../api/client";
import { ApiError } from "../../api/errors";
import { authorBookQueryKeys } from "../../api/queries";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthorBookPage } from "./author-book-page";

const sampleBook = {
  id: 12,
  seedKey: "ship",
  title: "Ship Inspections",
  author: "Jacob Grum",
  url: "https://books.example.test/ship",
} satisfies components["schemas"]["AuthorBookListItemResponse"];

const sampleDetails = {
  ...sampleBook,
} satisfies components["schemas"]["GetAuthorBookResponse"];

function renderAuthorBook(seedKey: string, withCachedCatalog = false) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  if (withCachedCatalog) {
    queryClient.setQueryData(authorBookQueryKeys.list(), { books: [sampleBook] });
  }

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/books/author/${seedKey}`]}>
        <Routes>
          <Route element={<AuthorBookPage />} path="/books/author/:seedKey" />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("public author-book details", () => {
  it("resolves a stable seed key through the catalog ID and shows the public book", async () => {
    const listBooks = vi.spyOn(publicApi, "listAuthorBooks").mockResolvedValue({ books: [sampleBook] });
    const getBook = vi.spyOn(publicApi, "getAuthorBook").mockResolvedValue(sampleDetails);

    renderAuthorBook("ship");

    expect(await screen.findByRole("heading", { name: "Ship Inspections" })).toBeInTheDocument();
    expect(screen.getByText((_, node) => node?.textContent === "By Jacob Grum")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open book link" })).toHaveAttribute("href", "https://books.example.test/ship");
    expect(screen.getByRole("link", { name: "Open book link" })).toHaveAttribute("rel", "noreferrer");
    expect(getBook).toHaveBeenCalledWith(12, expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(listBooks).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("link", { name: /back to the catalog/i })).toHaveAttribute("href", "/books");
  });

  it("shows not found when the seed key is absent from the public catalog", async () => {
    vi.spyOn(publicApi, "listAuthorBooks").mockResolvedValue({ books: [] });
    const getBook = vi.spyOn(publicApi, "getAuthorBook");

    renderAuthorBook("unknown");

    expect(await screen.findByRole("heading", { name: "This title is no longer on the shelf." })).toBeInTheDocument();
    expect(getBook).not.toHaveBeenCalled();
  });

  it("uses the fresh catalog query cache before making another list request", async () => {
    const listBooks = vi.spyOn(publicApi, "listAuthorBooks");
    const getBook = vi.spyOn(publicApi, "getAuthorBook").mockResolvedValue(sampleDetails);

    renderAuthorBook("ship", true);

    expect(await screen.findByRole("heading", { name: "Ship Inspections" })).toBeInTheDocument();
    expect(listBooks).not.toHaveBeenCalled();
    expect(getBook).toHaveBeenCalledWith(12, expect.objectContaining({ signal: expect.any(AbortSignal) }));
  });

  it("shows not found when a catalog item disappears before its detail read", async () => {
    vi.spyOn(publicApi, "listAuthorBooks").mockResolvedValue({ books: [sampleBook] });
    vi.spyOn(publicApi, "getAuthorBook").mockRejectedValue(new ApiError({ kind: "http", status: 404, message: "Not found" }));

    renderAuthorBook("ship");

    expect(await screen.findByRole("heading", { name: "This title is no longer on the shelf." })).toBeInTheDocument();
  });

  it("does not render unsafe external book URLs", async () => {
    vi.spyOn(publicApi, "listAuthorBooks").mockResolvedValue({ books: [sampleBook] });
    const getBook = vi.spyOn(publicApi, "getAuthorBook").mockResolvedValue({ ...sampleDetails, url: "javascript:alert(1)" });

    renderAuthorBook("ship");

    expect(await screen.findByText("No external book link has been shared for this title.")).toBeInTheDocument();
    expect(getBook).toHaveBeenCalled();
    expect(screen.queryByRole("link", { name: "Open book link" })).not.toBeInTheDocument();
  });
});
