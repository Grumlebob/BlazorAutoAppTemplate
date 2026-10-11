import { queryOptions } from "@tanstack/react-query";
import { publicApi } from "./client";

export const authorBookQueryKeys = {
  all: ["author-books"] as const,
  list: () => [...authorBookQueryKeys.all, "list"] as const,
  detail: (id: number | string) => [...authorBookQueryKeys.all, "detail", String(id)] as const,
};

export const authorBookQueries = {
  list: () =>
    queryOptions({
      queryKey: authorBookQueryKeys.list(),
      queryFn: ({ signal }) => publicApi.listAuthorBooks({ signal }),
    }),
  detail: (id: number | string) =>
    queryOptions({
      queryKey: authorBookQueryKeys.detail(id),
      queryFn: ({ signal }) => publicApi.getAuthorBook(id, { signal }),
    }),
};
