import { AuthorBookPage } from "../features/books/author-book-page";

export function meta() {
  return [
    { title: "Book details | The Authors Bookcase" },
    { name: "description", content: "Details for a book in the public catalog." },
  ];
}

export default function AuthorBookRoute() {
  return <AuthorBookPage />;
}
