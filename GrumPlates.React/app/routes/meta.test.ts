import { describe, expect, it } from "vitest";
import { meta as authorBookMeta } from "./author-book";
import { meta as booksMeta } from "./books";
import { meta as homeMeta } from "./home";

describe("route metadata", () => {
  it("provides a distinct title and description for each public route", () => {
    expect(homeMeta()).toEqual([
      { title: "The Authors Bookcase | Independent Books" },
      { name: "description", content: "Discover books shared by independent authors." },
    ]);
    expect(booksMeta()).toEqual([
      { title: "Books | The Authors Bookcase" },
      { name: "description", content: "Browse books shared by independent authors." },
    ]);
    expect(authorBookMeta()).toEqual([
      { title: "Book details | The Authors Bookcase" },
      { name: "description", content: "Details for a book in the public catalog." },
    ]);
  });
});
