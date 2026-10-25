# Recover registry capacity without changing release admission

**Historical record:** The repository-wide final and transfer byte caps and the publisher's byte-admission gate were removed on 2026-10-25. Main CI now records current GHCR usage and estimated incoming bundle bytes, then relies on the GHCR push result for actual provider errors. This plan records the earlier 1 GiB recovery path; do not use its byte-cap failure branch for current publication. The separate exact-reservation lock recovery remains covered by the shared registry workflow.

## Original failure and decision

Main CI `39066090388` attempt 1 passed validation and failed before any image publication with `payload store requires coordinated retention before publication`. Complete private payload inventory exceeded the fixed 1 GiB final-payload policy. This is a repository retention policy, not paid GitHub Actions storage or a billed GHCR quota. Registry retention's normal full-main-CI source gate creates a circular dependency while this condition persists.

The original fix added an explicit manual capacity-recovery proof to the existing registry workflow. It accepted only an exact current-main push/attempt with successful validation and a sole authenticated prepublication capacity failure. Every image build/publication step had to be skipped, all other jobs had to pass or be intentionally skipped, and the run/attempt/current-main identity was rechecked. Ordinary maintenance kept its successful-main source gate. Canonical registry protection, locking, ownership, reservation, and deletion receipts remained mandatory.

## Execution

Integrate the encrypted vault through its required PR gate. Establish genuine LocalCluster current and recovery markers with the two already-published compatible forward releases and migrations disabled. Never fabricate markers or apply the pending account migration. After this source passes exact-head PR CI and its exact-main run reaches only the verified capacity failure, use the explicit recovery run/attempt for preview, review its protected candidates, then apply bounded canonical retention. Re-inventory and verify exact absence before rerunning the failed publisher once on the same SHA.

## Verification

Fixture tests cover actual workflow input/default bindings, exact main/run/attempt provenance, passed validation, missing/duplicated/incomplete jobs, wrong/extra failures, unexpected publication activity, log reason and step timing, pagination, untrusted workflow contexts and changed main/attempts. A read-only historical fixture checks the real failure metadata and authenticated job log. No provider quota, production mutation or release is needed for these tests. PR/main identities and controlled execution receipts belong in the PR body and the cross-repository task plan.
