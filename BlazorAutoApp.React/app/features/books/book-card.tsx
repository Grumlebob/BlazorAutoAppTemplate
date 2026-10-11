import type { components } from "../../api/generated/schema";
import { Link } from "react-router";

type AuthorBookListItem = components["schemas"]["AuthorBookListItemResponse"];

export function BookCard({ book }: { book: AuthorBookListItem }) {
  const detailsPath = `/books/author/${encodeURIComponent(book.seedKey)}`;

  return (
    <article className="group overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm transition duration-200 hover:-translate-y-1 hover:border-indigo-200 hover:shadow-lg hover:shadow-indigo-950/5 motion-reduce:transform-none motion-reduce:transition-none">
      <div aria-hidden="true" className="relative flex aspect-[4/3] flex-col justify-between overflow-hidden bg-gradient-to-br from-indigo-950 via-indigo-800 to-sky-700 p-5 text-white sm:p-6">
        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-100">The public bookcase</span>
        <span className="absolute -right-10 top-8 size-36 rounded-full border border-white/20" />
        <span className="absolute -right-3 top-16 size-24 rounded-full border border-white/20" />
        <span className="relative max-w-[14rem] text-2xl font-semibold leading-tight tracking-tight sm:text-3xl">A story begins with a title.</span>
        <span className="relative w-fit rounded-full border border-white/30 bg-white/10 px-3 py-1 text-xs font-medium text-indigo-50">Independent work</span>
      </div>

      <div className="p-5 sm:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-800">Book</p>
        <h2 className="mt-2 text-xl font-semibold leading-snug tracking-tight text-slate-950">
          <Link className="rounded-sm underline decoration-transparent underline-offset-4 transition group-hover:decoration-indigo-300 hover:text-indigo-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700" to={detailsPath}>
            {book.title}
          </Link>
        </h2>
        <p className="mt-2 text-sm text-slate-700">By {book.author || "an independent author"}</p>
        <Link className="mt-5 inline-flex min-h-10 items-center gap-2 rounded-lg font-semibold text-indigo-800 hover:text-indigo-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700" to={detailsPath}>
          Explore this book
          <span aria-hidden="true" className="transition-transform group-hover:translate-x-1 motion-reduce:transition-none">→</span>
        </Link>
      </div>
    </article>
  );
}
