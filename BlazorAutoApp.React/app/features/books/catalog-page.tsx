import { useQuery } from "@tanstack/react-query";
import { authorBookQueries } from "../../api/queries";
import { BookCard } from "./book-card";
import { BookReadError, EmptyBooksState, LoadingState } from "./read-states";

export function CatalogPage() {
  const query = useQuery(authorBookQueries.list());
  const books = query.data?.books;

  return (
    <div className="space-y-8 sm:space-y-10">
      <section className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-indigo-800">The public shelf</p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950 sm:text-5xl">Books by independent authors.</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-700">Take a look through the collection. Each title leads to its author and any book link they have shared.</p>
      </section>

      {query.isPending && !query.data ? <LoadingState label="the public catalog" /> : null}
      {query.isError && !query.data ? <BookReadError error={query.error} onRetry={() => void query.refetch()} /> : null}
      {query.data && query.isError ? <BookReadError compact error={query.error} onRetry={() => void query.refetch()} /> : null}

      {query.isFetching && query.data ? <p className="text-sm text-slate-600" role="status">Refreshing the public catalog…</p> : null}

      {books?.length === 0 ? <EmptyBooksState /> : null}
      {books && books.length > 0 ? (
        <section aria-label="Public book listings">
          <div className="mb-5 flex items-baseline justify-between gap-4">
            <h2 className="text-lg font-semibold text-slate-950">Browse the collection</h2>
            <p className="text-sm text-slate-600">{books.length} {books.length === 1 ? "book" : "books"}</p>
          </div>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 sm:gap-6 lg:grid-cols-3">
            {books.map((book) => <BookCard book={book} key={book.seedKey} />)}
          </div>
        </section>
      ) : null}
    </div>
  );
}
