# Complete local CI report collection

## Decision

Complete zero-cost plan criteria 8.1 and 8.3 using the existing bounded report store. Inspection found browser diagnostics outside its configured source. Template also wrote packaged smoke TRX into a sibling directory; ImprovedDb did not request packaged browser TRX and skipped publisher report storage when failure preceded Trivy.

Copy available Playwright diagnostics into each terminal job source, retain packaged smoke TRX under that source, and preserve existing three-day success/seven-day failure retention, 1 GiB cap, pins, locks and private retrieval. Existing destinations and symlinks fail collection rather than overwrite unrelated content. No release transport, application behavior, schema, budget or hosting change is needed.

## Verification and integration

The regression fixture executes each actual terminal workflow step for a failed job, retrieves byte-identical smoke TRX, screenshots and traces, and rejects symlinks and collection collisions. Smoke fixtures verify actual result-directory routing. Deployment audits enforce the revised bindings. Run applicable Python, shell, workflow and deployment checks before the required exact-head CI. Compiled application/test inputs are unchanged; retain the already passing full local gate for those inputs.

Required PR/main results and integrated commit will be recorded in the PR body. A controlled application rollout is unnecessary for report collection; normal CI exercises it.
