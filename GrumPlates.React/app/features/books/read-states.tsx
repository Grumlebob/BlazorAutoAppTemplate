import { Link } from "react-router";
import { ApiError } from "../../api/errors";

export function LoadingState({ label, pageTitle }: { label: string; pageTitle?: string }) {
  return (
    <section aria-label={label} className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      {pageTitle ? <h1 className="sr-only" id="page-title">{pageTitle}</h1> : null}
      <div aria-hidden="true" className="space-y-4">
        <span className="block h-4 w-28 animate-pulse rounded-full bg-slate-200 motion-reduce:animate-none" />
        <span className="block h-7 w-3/4 animate-pulse rounded-full bg-slate-200 motion-reduce:animate-none" />
        <span className="block h-4 w-1/2 animate-pulse rounded-full bg-slate-100 motion-reduce:animate-none" />
      </div>
      <p className="mt-5 text-sm font-medium text-slate-700" role="status">Loading {label.toLowerCase()}…</p>
    </section>
  );
}

export function EmptyBooksState() {
  return (
    <section className="rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center sm:px-10">
      <span aria-hidden="true" className="mx-auto grid size-14 place-items-center rounded-2xl bg-indigo-50 text-indigo-800">
        <svg className="size-7" fill="none" viewBox="0 0 24 24">
          <path d="M4.75 5.5c2.86-.79 5.27-.26 7.25 1.3v12c-1.98-1.56-4.39-2.09-7.25-1.3v-12Zm14.5 0c-2.86-.79-5.27-.26-7.25 1.3v12c1.98-1.56 4.39-2.09 7.25-1.3v-12Z" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.6" />
        </svg>
      </span>
      <h2 className="mt-5 text-xl font-semibold tracking-tight text-slate-950">The shelf is quiet for now.</h2>
      <p className="mx-auto mt-2 max-w-md leading-7 text-slate-600">There are no public books to show yet. Check back when the collection grows.</p>
      <Link className="mt-6 inline-flex min-h-11 items-center rounded-full px-4 font-semibold text-indigo-800 underline decoration-indigo-300 underline-offset-4 hover:text-indigo-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700" to="/">
        Return home
      </Link>
    </section>
  );
}

export function BookNotFoundState() {
  return (
    <section className="mx-auto max-w-2xl rounded-3xl border border-slate-200 bg-white px-6 py-10 shadow-sm sm:px-10 sm:py-12">
      <p className="text-sm font-semibold uppercase tracking-[0.16em] text-indigo-800">Book not found</p>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl" id="page-title">This title is no longer on the shelf.</h1>
      <p className="mt-4 leading-7 text-slate-700">The book may have moved or its link may be out of date. You can return to the public catalog and choose another title.</p>
      <Link className="mt-7 inline-flex min-h-12 items-center justify-center rounded-full bg-indigo-700 px-6 py-3 font-semibold text-white transition hover:bg-indigo-800 focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-indigo-700" to="/books">
        Browse the books
      </Link>
    </section>
  );
}

export function BookReadError({ error, onRetry, compact = false, headingLevel = "h2" }: { error: unknown; onRetry: () => void; compact?: boolean; headingLevel?: "h1" | "h2" }) {
  const presentation = describeReadError(error);
  const Heading = headingLevel;

  return (
    <section aria-labelledby={headingLevel === "h1" ? "page-title" : "book-read-error-title"} className={`rounded-3xl border border-amber-200 bg-amber-50 ${compact ? "p-5" : "px-6 py-8 sm:px-8"}`} role="alert">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-900">Catalog update</p>
      <Heading className="mt-2 text-xl font-semibold tracking-tight text-slate-950" id={headingLevel === "h1" ? "page-title" : "book-read-error-title"}>{presentation.title}</Heading>
      <p className="mt-2 max-w-2xl leading-7 text-slate-700">{presentation.message}</p>
      {presentation.retryMessage ? <p className="mt-2 text-sm font-medium text-slate-700">{presentation.retryMessage}</p> : null}
      <button
        className="mt-5 inline-flex min-h-11 items-center justify-center rounded-full border border-amber-900/20 bg-white px-5 py-2 font-semibold text-amber-950 shadow-sm transition hover:bg-amber-100 focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-amber-900"
        onClick={onRetry}
        type="button"
      >
        Try again
      </button>
    </section>
  );
}

function describeReadError(error: unknown): { title: string; message: string; retryMessage?: string } {
  if (!(error instanceof ApiError)) {
    return { title: "Something went wrong.", message: "We couldn't load this public book information. Try again in a moment." };
  }

  if (error.kind === "network") {
    return { title: "The catalog is out of reach.", message: "Check your connection, then try again." };
  }

  if (error.kind === "invalid-response") {
    return { title: "We couldn't read the catalog.", message: "The service returned information we couldn't use. Try again shortly." };
  }

  if (error.status === 429) {
    const retrySeconds = error.retryAfterMs === undefined ? undefined : Math.ceil(error.retryAfterMs / 1_000);
    return {
      title: "The catalog is busy.",
      message: "Please give the public catalog a moment, then try again.",
      retryMessage: retrySeconds === undefined ? undefined : retrySeconds > 0 ? `You can try again in about ${retrySeconds} seconds.` : "You can try again now.",
    };
  }

  if (error.status !== undefined && error.status >= 500) {
    return { title: "The catalog is taking a break.", message: "The service is temporarily unavailable. Try again in a moment." };
  }

  return { title: "We couldn't load this book.", message: "The public catalog request could not be completed. Try again." };
}
