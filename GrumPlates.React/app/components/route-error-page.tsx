import { useEffect } from "react";
import { Link } from "react-router";

export function RouteErrorPage({ notFound }: { notFound: boolean }) {
  const title = notFound ? "Page not found" : "We couldn't load this page";

  useEffect(() => {
    document.title = `${title} | The Authors Bookcase`;
  }, [title]);

  return (
    <section aria-labelledby="page-title" className="mx-auto max-w-2xl rounded-3xl border border-slate-200 bg-white px-6 py-10 shadow-sm sm:px-10 sm:py-12" role="alert">
      <p className="text-sm font-semibold uppercase tracking-[0.16em] text-indigo-800">{notFound ? "Page not found" : "Unexpected error"}</p>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl" id="page-title">
        {notFound ? "This page couldn't be found." : "We couldn't load this page."}
      </h1>
      <p className="mt-4 leading-7 text-slate-700">
        {notFound
          ? "The address may be out of date. Browse the public catalog to find another title."
          : "Try again later, or return to the public home page."}
      </p>
      <Link className="mt-7 inline-flex min-h-12 items-center justify-center rounded-full bg-indigo-700 px-6 py-3 font-semibold text-white transition hover:bg-indigo-800 focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-indigo-700" to={notFound ? "/books" : "/"}>
        {notFound ? "Browse the books" : "Return home"}
      </Link>
    </section>
  );
}
