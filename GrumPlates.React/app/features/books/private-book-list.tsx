import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { components } from "../../api/generated/schema";
import { apiResult } from "../../api/api-result";
import { useAccounts } from "../accounts/account-context";

type Book = components["schemas"]["BookListItemResponse"];

// The route keys this view by application and owner. Deletion consent and errors
// belong to that view; the unsaved draft deliberately lives in the parent route.
export function PrivateBookList({ userId, editingDisabled, onEdit }: {
  userId: string;
  editingDisabled: boolean;
  onEdit: (book: Book) => void;
}) {
  const accounts = useAccounts();
  const client = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const queryKey = ["private", accounts.applicationId, userId, "books"];
  const books = useQuery({
    queryKey,
    enabled: !accounts.checking,
    queryFn: ({ signal }) => apiResult(accounts.api.GET("/api/books", { signal })),
    retry: false,
    staleTime: 0,
  });

  async function deleteBook(id: number) {
    setPending(true); setError("");
    try {
      await apiResult(accounts.api.DELETE("/api/books/{id}", { params: { path: { id } } }));
      setConfirmDelete(null);
      await client.invalidateQueries({ queryKey });
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not delete book.");
    } finally {
      setPending(false);
    }
  }

  return <>
    {books.isPending && <p className="mt-6" role="status">Loading books…</p>}
    {books.error && <div className="mt-6">
      <p className="text-red-800" role="alert">{books.error.message}</p>
      <button className="mt-3 text-indigo-700 disabled:opacity-50" disabled={books.isFetching} onClick={() => void books.refetch()}>Try again</button>
    </div>}
    {error && <p className="mt-6 text-red-800" role="alert">{error}</p>}
    <ul className="mt-6 grid gap-4 sm:grid-cols-2">
      {books.data?.books?.map(book => <li className="rounded-xl border border-slate-200 bg-white p-5" key={book.id}>
        <h2 className="font-semibold">{book.title}</h2><p className="mt-1 text-slate-600">{book.author}</p>
        <div className="mt-4 flex flex-wrap gap-4 text-sm font-medium">
          <button disabled={pending || editingDisabled} onClick={() => { setConfirmDelete(null); onEdit(book); }}>Edit</button>
          {confirmDelete !== book.id
            ? <button className="text-red-800" disabled={pending} onClick={() => setConfirmDelete(book.id!)}>Delete</button>
            : <>
              <span>Permanently delete?</span>
              <button className="text-red-800" disabled={pending} onClick={() => void deleteBook(book.id!)}>Confirm delete</button>
              <button disabled={pending} onClick={() => setConfirmDelete(null)}>Cancel</button>
            </>}
        </div>
      </li>)}
    </ul>
    {books.data?.books?.length === 0 && <p className="mt-6">No books yet. Add your first below.</p>}
  </>;
}
