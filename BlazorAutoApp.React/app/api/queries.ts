import { queryOptions } from "@tanstack/react-query";
import { publicApi } from "./client";
import { invalidApiResponse } from "./errors";

export const authorBookQueryKeys = {
  all: ["author-books"] as const,
  list: () => [...authorBookQueryKeys.all, "list"] as const,
  detail: (id: number | string) => [...authorBookQueryKeys.all, "detail", String(id)] as const,
  bySeedKey: (seedKey: string) => [...authorBookQueryKeys.all, "seed-key", seedKey] as const,
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
  bySeedKey: (seedKey: string) =>
    queryOptions({
      queryKey: authorBookQueryKeys.bySeedKey(seedKey),
      queryFn: async ({ signal, client }) => {
        const cachedCatalog = client.getQueryData<Awaited<ReturnType<typeof publicApi.listAuthorBooks>>>(authorBookQueryKeys.list());
        const catalog = cachedCatalog ?? await publicApi.listAuthorBooks({ signal });
        const summary = catalog.books.find((book) => book.seedKey === seedKey);
        if (!summary) {
          return null;
        }

        if (summary.id === undefined || summary.id === null) {
          throw invalidApiResponse(200);
        }

        return publicApi.getAuthorBook(summary.id, { signal });
      },
    }),
};
