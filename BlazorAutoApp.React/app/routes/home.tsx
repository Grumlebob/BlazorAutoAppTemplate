export function meta() {
  return [{ title: "The Authors Bookcase" }, { name: "description", content: "A public catalog of books by independent authors." }];
}

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col justify-center px-6 py-16 sm:px-10">
      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-indigo-700">Public catalog</p>
      <h1 className="mt-4 text-4xl font-bold tracking-tight text-slate-950 sm:text-6xl">The Authors Bookcase</h1>
      <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
        Browse books by independent authors. The catalog is coming soon.
      </p>
    </main>
  );
}
