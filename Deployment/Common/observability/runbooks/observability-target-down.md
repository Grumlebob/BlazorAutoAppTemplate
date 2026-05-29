# Observability Target Down

Prometheus reports that a scrape target is down.

1. Check whether the container or systemd service is running.
2. Check the target service logs for startup or bind errors.
3. Confirm the target is reachable on the private/local network only.
4. If the target is Alloy, inspect Alloy component health before restarting it.
5. After recovery, verify Prometheus marks the target as up again.
