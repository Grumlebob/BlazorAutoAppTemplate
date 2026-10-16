import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { apiResult } from "../features/accounts/account-api";
import { useAccounts } from "../features/accounts/account-context";

export function meta() { return [{ title: "My books | The Authors Bookcase" }]; }

export default function MyBooks() {
  const accounts = useAccounts();
  const client = useQueryClient();
  const userId = accounts.session.user?.id;
  const ownerKey = userId ?? "anonymous";
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [url, setUrl] = useState("");
  const [editing, setEditing] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [draftOwner, setDraftOwner] = useState<string | null>(null);
  const hasDraft = !!title || !!author || !!url || editing !== null;
  const otherOwner = hasDraft && draftOwner !== null && draftOwner !== ownerKey;
  const books = useQuery({ queryKey: ["private", userId, "books"], enabled: !!userId && !accounts.checking,
    queryFn: ({ signal }) => apiResult(accounts.api.GET("/api/books", { signal })), retry: false, staleTime: 0 });

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (otherOwner) return;
    setPending(true); setError("");
    try {
      const body = { title, author: author || null, url: url || null };
      if (editing !== null) await apiResult(accounts.api.PUT("/api/books/{id}", { params: { path: { id: editing } }, body: { ...body, id: editing } }));
      else await apiResult(accounts.api.POST("/api/books", { body }));
      setTitle(""); setAuthor(""); setUrl(""); setEditing(null);
      await client.invalidateQueries({ queryKey: ["private", userId] });
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Could not save your book."); }
    finally { setPending(false); }
  }

  return <section>
    <h1 className="text-3xl font-semibold tracking-tight" id="page-title">My books</h1>
    <p className="mt-3 text-slate-600">Your private collection.</p>
    {accounts.loading || accounts.checking ? <p className="mt-6" role="status">Checking your session…</p>
      : !userId ? <p className="mt-6">{accounts.error ?? "Sign in to view and save your private books."} <Link className="text-indigo-700" to="/auth/login?returnTo=/my-books">Sign in</Link></p>
        : <>
          {books.isPending && <p className="mt-6" role="status">Loading books…</p>}
          {books.error && <p className="mt-6 text-red-800" role="alert">{books.error.message}</p>}
          <ul className="mt-6 grid gap-4 sm:grid-cols-2">
            {books.data?.books?.map(book => <li className="rounded-xl border border-slate-200 bg-white p-5" key={book.id}>
              <h2 className="font-semibold">{book.title}</h2><p className="mt-1 text-slate-600">{book.author}</p>
              <div className="mt-4 flex flex-wrap gap-4 text-sm font-medium">
              <button disabled={pending} onClick={() => { setDraftOwner(ownerKey); setEditing(book.id!); setTitle(book.title ?? ""); setAuthor(book.author ?? ""); setUrl(book.url ?? ""); setConfirmDelete(null); }}>Edit</button>
                {confirmDelete !== book.id ? <button className="text-red-800" onClick={() => setConfirmDelete(book.id!)}>Delete</button> : <>
                  <span>Permanently delete?</span><button className="text-red-800" disabled={pending} onClick={async () => {
                    setPending(true); setError("");
                    try { await apiResult(accounts.api.DELETE("/api/books/{id}", { params: { path: { id: book.id! } } })); setConfirmDelete(null); await client.invalidateQueries({ queryKey: ["private", userId] }); }
                    catch (failure) { setError(failure instanceof Error ? failure.message : "Could not delete book."); }
                    finally { setPending(false); }
                  }}>Confirm delete</button><button onClick={() => setConfirmDelete(null)}>Cancel</button>
                </>}
              </div>
            </li>)}
          </ul>
          {books.data?.books?.length === 0 && <p className="mt-6">No books yet. Add your first below.</p>}
        </>}
    {error && <p className="mt-6 text-red-800" role="alert">{error}</p>}
    {otherOwner ? <div className="mt-8"><p>This draft belongs to another session. Discard it before continuing.</p><button className="mt-4 text-indigo-700" onClick={() => { setTitle(""); setAuthor(""); setUrl(""); setEditing(null); setError(""); setDraftOwner(ownerKey); }}>Discard previous draft</button></div> : <form className="mt-8 max-w-lg space-y-4 rounded-xl border border-slate-200 bg-white p-6" onSubmit={save}>
      <h2 className="text-xl font-semibold">{editing === null ? "Add a book" : "Edit book"}</h2>
      <p className="text-sm text-slate-600">Your input stays here if your session expires. Sign in before saving.</p>
      <label className="block font-medium">Title<input className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2" required maxLength={200} value={title} onChange={event => { setDraftOwner(ownerKey); setTitle(event.target.value); }} /></label>
      <label className="block font-medium">Author<input className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2" maxLength={200} value={author} onChange={event => { setDraftOwner(ownerKey); setAuthor(event.target.value); }} /></label>
      <label className="block font-medium">Website<input className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2" type="url" maxLength={2048} value={url} onChange={event => { setDraftOwner(ownerKey); setUrl(event.target.value); }} /></label>
      <button className="rounded-lg bg-indigo-700 px-5 py-2.5 font-medium text-white disabled:opacity-50" disabled={pending || accounts.checking || !userId}>{pending ? "Saving…" : "Save book"}</button>
      {editing !== null && <button className="ml-4 text-sm" type="button" onClick={() => { setEditing(null); setTitle(""); setAuthor(""); setUrl(""); setDraftOwner(ownerKey); }}>Cancel editing</button>}
    </form>}
  </section>;
}
