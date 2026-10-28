import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import type { components } from "../../api/generated/schema";
import { authorBookQueries } from "../../api/queries";
import { ApiError } from "../../api/errors";
import { BookNotFoundState, BookReadError, LoadingState } from "./read-states";

type AuthorBookDetails = components["schemas"]["GetAuthorBookResponse"];

export function AuthorBookPage() {
  const { seedKey } = useParams();
  const query = useQuery({ ...authorBookQueries.bySeedKey(seedKey ?? ""), enabled: Boolean(seedKey) });
  const bookTitle = query.data?.title;

  useEffect(() => {
    document.title = `${bookTitle ?? "Book details"} | The Authors Bookcase`;
  }, [bookTitle]);

  if (!seedKey || query.data === null || isBookNotFound(query.error)) {
    return <BookNotFoundState />;
  }

  if (query.isPending && !query.data) {
    return <LoadingState label="book details" pageTitle="Book details" />;
  }

  if (query.isError && !query.data) {
    return <BookReadError error={query.error} headingLevel="h1" onRetry={() => void query.refetch()} />;
  }

  if (!query.data) {
    return <LoadingState label="book details" pageTitle="Book details" />;
  }

  return (
    <div className="space-y-6">
      <Link className="inline-flex min-h-10 items-center gap-2 rounded-lg font-semibold text-indigo-800 hover:text-indigo-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700" to="/books">
        <span aria-hidden="true">←</span>
        Back to the catalog
      </Link>
      {query.isError ? <BookReadError compact error={query.error} onRetry={() => void query.refetch()} /> : null}
      <BookDetails book={query.data} />
    </div>
  );
}

function BookDetails({ book }: { book: AuthorBookDetails }) {
  const externalUrl = safeBookUrl(book.url);

  return (
    <article className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
      <div className="grid md:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div aria-hidden="true" className="flex min-h-64 flex-col justify-between bg-gradient-to-br from-indigo-950 via-indigo-800 to-sky-700 p-7 text-white sm:p-10 md:min-h-[30rem]">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-100">The public bookcase</p>
          <div className="relative z-10 max-w-sm">
            <span className="mb-5 block h-1 w-12 rounded-full bg-emerald-300" />
            <p className="text-3xl font-semibold leading-tight tracking-tight sm:text-4xl">{book.title}</p>
            <p className="mt-3 text-lg text-indigo-100">{book.author || "Independent author"}</p>
          </div>
          <span className="w-fit rounded-full border border-white/30 bg-white/10 px-3 py-1 text-xs font-medium text-indigo-50">Book listing</span>
        </div>

        <div className="flex flex-col justify-center p-6 sm:p-10 lg:p-14">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-indigo-800">Book details</p>
          <h1 className="mt-4 break-words text-4xl font-semibold leading-tight tracking-tight text-slate-950 sm:text-5xl" id="page-title">{book.title}</h1>
          <p className="mt-5 text-lg text-slate-700">By <span className="font-semibold text-slate-950">{book.author || "an independent author"}</span></p>
          <p className="mt-5 max-w-xl leading-7 text-slate-700">This title is part of the public collection. Visit the shared book link to learn more.</p>
          {externalUrl ? (
            <a className="mt-8 inline-flex min-h-12 w-fit items-center justify-center gap-3 rounded-full bg-indigo-700 px-6 py-3 font-semibold text-white shadow-sm shadow-indigo-950/15 transition hover:bg-indigo-800 focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-indigo-700" href={externalUrl} rel="noreferrer" target="_blank">
              Open book link
              <span aria-hidden="true">↗</span>
            </a>
          ) : (
            <p className="mt-8 rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-700">No external book link has been shared for this title.</p>
          )}
        </div>
      </div>
    </article>
  );
}

function isBookNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.kind === "http" && error.status === 404;
}

function safeBookUrl(value: string | null | undefined): string | undefined {
  if (!value) {
    return undefined;
  }

  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : undefined;
  } catch {
    return undefined;
  }
}
