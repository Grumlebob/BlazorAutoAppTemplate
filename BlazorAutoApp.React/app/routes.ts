import { index, route, type RouteConfig } from "@react-router/dev/routes";

export default [
  index("./routes/home.tsx"),
  route("books", "./routes/books.tsx"),
  route("books/author/:seedKey", "./routes/author-book.tsx"),
] satisfies RouteConfig;
