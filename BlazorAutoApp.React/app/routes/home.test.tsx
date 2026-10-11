import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Home from "./home";

describe("home route scaffold", () => {
  it("shows the public catalog placeholder without account controls", () => {
    render(<Home />);

    expect(screen.getByRole("heading", { name: "The Authors Bookcase" })).toBeInTheDocument();
    expect(screen.getByText("Browse books by independent authors. The catalog is coming soon.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /log in|sign in|account/i })).not.toBeInTheDocument();
  });
});
