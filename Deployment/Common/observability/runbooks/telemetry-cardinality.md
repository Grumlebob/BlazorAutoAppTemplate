# Telemetry Cardinality

High cardinality usually means a label contains unbounded values.

1. In Prometheus, inspect active series by metric and label.
2. Look for labels containing IDs, URLs with IDs, user input, titles, emails, or request bodies.
3. Fix instrumentation or relabeling at the source.
4. Keep labels to low-cardinality dimensions such as service, environment, operation, outcome, node, and status code.
5. Re-run the cardinality check after the fix.
