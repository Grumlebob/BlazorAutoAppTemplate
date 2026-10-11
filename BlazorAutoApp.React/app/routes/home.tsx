import { Link } from "react-router";

export function meta() {
  return [
    { title: "The Authors Bookcase | Independent Books" },
    { name: "description", content: "Discover books shared by independent authors." },
  ];
}

export default function Home() {
  return (
    <div className="space-y-16 sm:space-y-20">
      <section className="grid items-center gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(18rem,0.9fr)] lg:gap-14">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-indigo-800">A public shelf for independent voices</p>
          <h1 className="mt-5 text-4xl font-semibold leading-tight tracking-tight text-slate-950 sm:text-5xl lg:text-6xl">
            Find a book that stays with you.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-slate-700">
            Explore books shared by independent authors. Start with the catalog, then follow a title to its author and book link.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Link
              className="inline-flex min-h-12 items-center justify-center gap-3 rounded-full bg-indigo-700 px-6 py-3 font-semibold text-white shadow-sm shadow-indigo-950/15 transition hover:bg-indigo-800 focus-visible:outline-2 focus-visible:outline-offset-3 focus-visible:outline-indigo-700"
              to="/books"
            >
              Browse the books
              <span aria-hidden="true">→</span>
            </Link>
            <p className="px-1 text-sm text-slate-600">Open to everyone. No account needed.</p>
          </div>
        </div>

        <div className="relative isolate overflow-hidden rounded-[2rem] bg-indigo-950 px-6 py-8 text-white shadow-xl shadow-indigo-950/10 sm:px-9 sm:py-10">
          <div aria-hidden="true" className="absolute -right-16 -top-20 -z-10 size-64 rounded-full bg-indigo-700/70 blur-3xl" />
          <div aria-hidden="true" className="absolute -bottom-20 -left-16 -z-10 size-56 rounded-full bg-sky-500/30 blur-3xl" />
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-indigo-200">The public bookcase</p>
          <div className="mt-10 grid grid-cols-[auto_minmax(0,1fr)] items-center gap-5">
            <div aria-hidden="true" className="grid size-20 place-items-center rounded-2xl border border-white/20 bg-white/10 text-3xl font-light text-indigo-100 sm:size-24 sm:text-4xl">
              Aa
            </div>
            <div>
              <p className="text-2xl font-semibold tracking-tight sm:text-3xl">A good story travels.</p>
              <p className="mt-2 text-sm leading-6 text-indigo-100">Every title opens a path to the person who wrote it.</p>
            </div>
          </div>
          <div className="mt-10 flex items-center gap-3 border-t border-white/20 pt-5 text-sm text-indigo-100">
            <span aria-hidden="true" className="size-2 rounded-full bg-emerald-300" />
            A growing collection of independent work
          </div>
        </div>
      </section>

      <section aria-labelledby="welcome-heading" className="grid gap-6 border-t border-slate-200 pt-8 sm:grid-cols-3 sm:gap-8 sm:pt-10">
        <h2 className="sr-only" id="welcome-heading">A simple way to discover books</h2>
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-indigo-800">01 / Browse</p>
          <p className="mt-3 text-lg font-semibold text-slate-950">Find a title that catches your eye.</p>
        </div>
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-indigo-800">02 / Discover</p>
          <p className="mt-3 text-lg font-semibold text-slate-950">Meet the author behind the book.</p>
        </div>
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-indigo-800">03 / Follow</p>
          <p className="mt-3 text-lg font-semibold text-slate-950">Open the book link and keep reading.</p>
        </div>
      </section>
    </div>
  );
}
