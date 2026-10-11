import type { ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { Links, Meta, Scripts, ScrollRestoration } from "react-router";
import stylesheet from "./app.css?url";
import { SiteShell } from "./components/site-shell";
import { queryClient } from "./api/query-client";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <SiteShell />
    </QueryClientProvider>
  );
}

export function links() {
  return [{ rel: "stylesheet", href: stylesheet }];
}
