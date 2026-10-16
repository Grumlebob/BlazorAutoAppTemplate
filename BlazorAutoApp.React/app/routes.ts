import { index, route, type RouteConfig } from "@react-router/dev/routes";

export default [
  index("./routes/home.tsx"),
  route("auth", "./routes/auth-index.tsx"),
  route("books", "./routes/books.tsx"),
  route("books/author/:seedKey", "./routes/author-book.tsx"),
  route("auth/:action", "./routes/account.tsx"),
  route("my-books", "./routes/my-books.tsx"),
] satisfies RouteConfig;
