import { CatalogPage } from "../features/books/catalog-page";

export function meta() {
  return [
    { title: "Books | The Authors Bookcase" },
    { name: "description", content: "Browse books shared by independent authors." },
  ];
}

export default function BooksRoute() {
  return <CatalogPage />;
}
