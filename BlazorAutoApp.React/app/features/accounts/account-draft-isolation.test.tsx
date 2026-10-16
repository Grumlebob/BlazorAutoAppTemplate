import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, expect, it, vi } from "vitest";
import MyBooks from "../../routes/my-books";
import AccountPage from "../../routes/account";
import { AccountProvider } from "./account-provider";

const clients: QueryClient[] = [];
afterEach(() => {
  cleanup();
  clients.splice(0).forEach(client => client.clear());
  vi.unstubAllGlobals();
});

it("hides private book drafts while checking and preserves them only for their original owner", async () => {
  const state = { owner: "user-a" as string | null, pendingSession: undefined as Promise<Response> | undefined };
  const writes = renderApp("/my-books", state);
  const user = userEvent.setup();
  await waitFor(() => expect(screen.getByRole("button", { name: "Save book" })).toBeEnabled());
  await user.type(screen.getByRole("textbox", { name: "Title" }), "Alice's private draft");

  let finishSession!: (response: Response) => void;
  state.pendingSession = new Promise(resolve => { finishSession = resolve; });
  fireEvent.focus(window);
  await screen.findByText("Checking your session…");
  expect(screen.queryByRole("textbox", { name: "Title" })).not.toBeInTheDocument();
  state.pendingSession = undefined;
  finishSession(json(session(state.owner)));
  expect(await screen.findByRole("textbox", { name: "Title" })).toHaveValue("Alice's private draft");

  state.owner = null;
  fireEvent.focus(window);
  await screen.findByRole("button", { name: "Discard previous draft" });
  expect(screen.queryByDisplayValue("Alice's private draft")).not.toBeInTheDocument();
  state.owner = "user-a";
  fireEvent.focus(window);
  expect(await screen.findByRole("textbox", { name: "Title" })).toHaveValue("Alice's private draft");

  state.owner = "user-b";
  fireEvent.focus(window);
  await user.click(await screen.findByRole("button", { name: "Discard previous draft" }));
  expect(screen.getByRole("textbox", { name: "Title" })).toHaveValue("");
  await user.type(screen.getByRole("textbox", { name: "Title" }), "Bob's own draft");
  await user.click(screen.getByRole("button", { name: "Save book" }));
  await waitFor(() => expect(writes).toEqual([{ owner: "user-b", title: "Bob's own draft" }]));
});

it("clears account-management credentials, proposed email and deletion consent when the owner changes", async () => {
  const state = { owner: "user-a" as string | null, pendingSession: undefined as Promise<Response> | undefined };
  renderApp("/auth/settings", state);
  const user = userEvent.setup();
  await screen.findByText("user-a@example.test");
  await user.type(screen.getByLabelText("Current password"), "Alice current secret");
  await user.type(screen.getByLabelText("New password"), "Alice replacement secret");
  await user.type(screen.getByRole("textbox", { name: "New email" }), "alice-new@example.test");
  await user.click(screen.getByRole("checkbox"));

  state.owner = "user-b";
  fireEvent.focus(window);
  await screen.findByText("user-b@example.test");

  expect(screen.getByLabelText("Current password")).toHaveValue("");
  expect(screen.getByLabelText("New password")).toHaveValue("");
  expect(screen.getByRole("textbox", { name: "New email" })).toHaveValue("");
  expect(screen.getByRole("checkbox")).not.toBeChecked();
});

it("does not reuse a private draft in another application with the same user ID", async () => {
  const state = { owner: "user-a", applicationId: "a".repeat(32) };
  const writes = renderApp("/my-books", state);
  const user = userEvent.setup();
  await waitFor(() => expect(screen.getByRole("button", { name: "Save book" })).toBeEnabled());
  await user.type(screen.getByRole("textbox", { name: "Title" }), "Original application's private draft");

  state.applicationId = "b".repeat(32);
  fireEvent.focus(window);

  await screen.findByRole("button", { name: "Discard previous draft" });
  expect(screen.queryByDisplayValue("Original application's private draft")).not.toBeInTheDocument();
  expect(writes).toEqual([]);
});

function renderApp(path: string, state: { owner: string | null; pendingSession?: Promise<Response>; applicationId?: string }) {
  const writes: { owner: string | null; title: unknown }[] = [];
  vi.stubGlobal("fetch", async (request: Request) => {
    switch (new URL(request.url).pathname) {
      case "/api/client-config": return json({ schemaVersion: 1, accountsEnabled: true, applicationId: state.applicationId ?? "a".repeat(32) });
      case "/api/auth/session": return state.pendingSession ?? json(session(state.owner));
      case "/api/books": {
        if (request.method === "GET") return json({ books: [] });
        const body = await request.json() as { title: unknown };
        writes.push({ owner: request.headers.get("X-Expected-User"), title: body.title });
        return json({ id: 1, title: body.title }, 201);
      }
      default: return json({ title: "Not found" }, 404);
    }
  });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  clients.push(client);
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><AccountProvider>
    <Routes>
      <Route path="/my-books" element={<MyBooks />} />
      <Route path="/auth/:action" element={<AccountPage />} />
    </Routes>
  </AccountProvider></MemoryRouter></QueryClientProvider>);
  return writes;
}

function session(owner: string | null) {
  return {
    enabled: true, registrationEnabled: true, emailEnabled: true, csrfToken: "fixture-csrf",
    user: owner ? { id: owner, email: `${owner}@example.test`, roles: [] } : null,
  };
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}
