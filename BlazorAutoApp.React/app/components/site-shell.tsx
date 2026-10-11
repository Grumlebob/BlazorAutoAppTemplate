import type { ReactNode } from "react";
import { Link, NavLink, Outlet } from "react-router";

export function SiteShell({ children }: { children?: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-950">
      <a
        className="sr-only z-50 rounded-md bg-white px-4 py-3 text-slate-950 shadow-lg focus:fixed focus:left-4 focus:top-4 focus:not-sr-only focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700"
        href="#main-content"
        onClick={() => document.getElementById("main-content")?.focus()}
      >
        Skip to content
      </a>

      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <Link aria-label="The Authors Bookcase home" className="flex w-fit items-center gap-3 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-700" to="/">
            <span aria-hidden="true" className="grid size-11 place-items-center rounded-xl bg-indigo-700 text-white shadow-sm shadow-indigo-950/15">
              <svg className="size-6" fill="none" viewBox="0 0 24 24">
                <path d="M4.75 5.5c2.86-.79 5.27-.26 7.25 1.3v12c-1.98-1.56-4.39-2.09-7.25-1.3v-12Zm14.5 0c-2.86-.79-5.27-.26-7.25 1.3v12c1.98-1.56 4.39-2.09 7.25-1.3v-12Z" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.6" />
              </svg>
            </span>
            <span className="flex flex-col">
              <span className="font-semibold tracking-tight text-slate-950">The Authors Bookcase</span>
              <span className="text-xs text-slate-600">Independent books, collected.</span>
            </span>
          </Link>

          <nav aria-label="Main navigation" className="flex items-center gap-2">
            <NavLink
              className={({ isActive }) =>
                `rounded-full px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700 ${
                  isActive ? "bg-indigo-50 text-indigo-900" : "text-slate-700 hover:bg-slate-100 hover:text-slate-950"
                }`
              }
              end
              to="/"
            >
              Home
            </NavLink>
            <NavLink
              className={({ isActive }) =>
                `rounded-full px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-700 ${
                  isActive ? "bg-indigo-50 text-indigo-900" : "text-slate-700 hover:bg-slate-100 hover:text-slate-950"
                }`
              }
              to="/books"
            >
              Books
            </NavLink>
          </nav>
        </div>
      </header>

      <main aria-labelledby="page-title" className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6 sm:py-14 lg:px-8" id="main-content" tabIndex={-1}>
        {children ?? <Outlet />}
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-4 py-6 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <p className="font-medium text-slate-800">A small shelf for independent voices.</p>
          <p>Open to everyone. No account needed.</p>
        </div>
      </footer>
    </div>
  );
}
