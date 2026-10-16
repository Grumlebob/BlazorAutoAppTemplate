import { useState, type ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { isRouteErrorResponse, Links, Meta, Scripts, ScrollRestoration, useRouteError } from "react-router";
import stylesheet from "./app.css?url";
import { createQueryClient } from "./api/query-client";
import { RouteErrorPage } from "./components/route-error-page";
import { RouteFocusManager } from "./components/route-focus-manager";
import { SiteShell } from "./components/site-shell";
import { AccountProvider } from "./features/accounts/account-provider";

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
        <RouteFocusManager />
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

export function ErrorBoundary() {
  const error = useRouteError();
  const notFound = isRouteErrorResponse(error) && error.status === 404;

  return (
    <SiteShell>
      <RouteErrorPage notFound={notFound} />
    </SiteShell>
  );
}

export default function App() {
  const [queryClient] = useState(createQueryClient);
  return (
    <QueryClientProvider client={queryClient}>
      <AccountProvider><SiteShell /></AccountProvider>
    </QueryClientProvider>
  );
}

export function links() {
  return [{ rel: "stylesheet", href: stylesheet }];
}
