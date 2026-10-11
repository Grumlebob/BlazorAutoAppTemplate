import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./errors";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 300_000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
      retry: (failureCount, error) => {
        if (!(error instanceof ApiError) || failureCount >= 1) {
          return false;
        }

        if (error.kind === "network") {
          return true;
        }

        return error.kind === "http" && (error.status === 502 || error.status === 503 || error.status === 504);
      },
      retryDelay: (attempt, error) =>
        error instanceof ApiError && error.retryAfterMs !== undefined
          ? error.retryAfterMs
          : Math.min(1_000 * 2 ** attempt, 30_000),
    },
  },
});
