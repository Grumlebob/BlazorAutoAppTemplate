import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState } from "react";
import { Link, MemoryRouter, Route, Routes, useNavigate } from "react-router";
import { describe, expect, it } from "vitest";
import { RouteFocusManager } from "./route-focus-manager";

function CatalogPage() {
  const navigate = useNavigate();

  return (
    <>
      <h1 id="page-title">Book catalog</h1>
      <Link to="/books/author/ship">Open book</Link>
      <button onClick={() => navigate(1)} type="button">Browser forward</button>
    </>
  );
}

function DetailsPage() {
  const navigate = useNavigate();
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setLoaded(true), 50);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <>
      <h1 id="page-title">{loaded ? "Ship Inspections" : "Loading book details"}</h1>
      <button onClick={() => navigate(-1)} type="button">Browser back</button>
    </>
  );
}

describe("route focus management", () => {
  it("keeps focus on the page region through loading, data and history navigation", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/books"]}>
        <RouteFocusManager />
        <main aria-labelledby="page-title" id="main-content" tabIndex={-1}>
          <Routes>
            <Route element={<CatalogPage />} path="/books" />
            <Route element={<DetailsPage />} path="/books/author/:seedKey" />
          </Routes>
        </main>
      </MemoryRouter>,
    );

    const catalogHeading = screen.getByRole("heading", { name: "Book catalog" });
    expect(catalogHeading).not.toHaveFocus();

    await user.click(screen.getByRole("link", { name: "Open book" }));
    expect(screen.getByRole("heading", { name: "Loading book details" })).toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Loading book details" })).toHaveFocus();
    expect(await screen.findByRole("heading", { name: "Ship Inspections" })).toBeInTheDocument();
    const detailMain = screen.getByRole("main", { name: "Ship Inspections" });
    expect(detailMain).toHaveFocus();

    await user.click(screen.getByRole("button", { name: "Browser back" }));
    expect(await screen.findByRole("heading", { name: "Book catalog" })).toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Book catalog" })).toHaveFocus();

    await user.click(screen.getByRole("button", { name: "Browser forward" }));
    expect(screen.getByRole("heading", { name: "Loading book details" })).toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Loading book details" })).toHaveFocus();
    expect(await screen.findByRole("heading", { name: "Ship Inspections" })).toBeInTheDocument();
    expect(screen.getByRole("main", { name: "Ship Inspections" })).toHaveFocus();
  });
});
