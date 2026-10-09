# Goal prompt: BlazorAutoAppTemplate upgrade and LocalSingleNode

Paste the block below as a new goal. It runs [BlazorAutoAppTemplateUpgrade.md](BlazorAutoAppTemplateUpgrade.md) to the end and authorises everything the plan specifies:

- the D15 security fix (seeded demo accounts disabled in deployments);
- merging the P7, P8, P10 and P11 stack;
- closing superseded Dependabot PRs and setting the `DEPLOY_TARGETS`/`LOCALSINGLENODE_*` repository variables (Q5);
- the P12 closeout;
- the four P13 PRs;
- CD deploys to node-demo only (Q4).

Execution context (operator-confirmed 2026-10-09): this agent runs on the Windows **main PC**, not node-demo. **node-demo is a separate PC at `192.168.0.212`, with a fixed DHCP lease.** The intended site after deployment is `http://192.168.0.212/`, also `http://node-demo.local/` when mDNS resolves. Keep those values in the plan and handoff only; reusable deployment configuration still detects machine facts.

The operator confirmed on 2026-10-09 that node-demo is installed and the repository is cloned; no further setup has been done. MB5 and the clone part of MB6 are complete. The remaining operator part is MB6–MB7 (P13.D), on node-demo: authenticate if needed, ask a local agent "set it up, you are node-demo; fixed lease 192.168.0.212", and paste the one sudo command it prints. Do not reinstall or clone over the existing directory. The main-PC agent runs the required independent LAN acceptance check itself. MB9 (deleting old seeded accounts) is optional. LocalCluster and Cloud deploys stay forbidden (Q1).

```text
/goal Complete Plans/BlazorAutoAppTemplateUpgrade.md end to end in this repository (Grumlebob/BlazorAutoAppTemplate), adopting every decision in section 10 (Q1-Q9) and P13.A (S1-S21) without asking again. Done = 11.2 items 0, 1, 2, 4 and 5 finished, the P13.12 table all passing, evidence in 11.1, status line "complete".

You are on the operator's main PC (Windows hostname DESKTOP-FDU51L5 as observed on 2026-10-09). You are not node-demo. node-demo is the separate target at 192.168.0.212, with a fixed DHCP lease. Do repository work and GitHub operations here; never run node bootstrap, runner installation, hostname changes or node firewall changes on the main PC or its WSL distributions. Node setup belongs to the local agent and operator on node-demo.

Read the plan's "How to use this plan" note, then the template AGENTS.md and docs/Test.md, then plan sections 3 (follow 3.0: prepare WSL/Docker prerequisites and use WSL for implementation and gates), 9, 10 and 11. Section 11 contains historical phase evidence and newer environment facts: re-verify each SHA, branch, PR and CI run before acting on it. Do not assume the old main SHA or branch stack is still current.

Preflight first: preserve the current uncommitted plan/config edits. Ubuntu-24.04 is now WSL 2; /home/grumbo/src/BlazorAutoAppTemplate is prepared with Docker integration, SDK 10.0.303, pwsh and the gate tools (11.6). Windows and WSL main match the observed origin/main. Recheck fetch, SDK selection, gh authentication, Ansible --check and Docker access before implementation; do not repeat installation or repurpose ImprovedDb-CI. GitHub main currently has no branch protection or effective rules: enforce the exact-head build-test-push and green-main gates yourself, and do not change protection under Q5. Node-demo's missing runner and unavailable SSH/HTTP are pending P13 setup, not blockers for the earlier repository phases.

Rules: one PR per step group; squash-merge only when build-test-push is green on the exact head (gh pr merge --squash --match-head-commit), then wait for green main CI (validate and publish) before the next PR. Run the 3.6 gate before every push. Fix failures properly; never skip, disable or weaken a test or audit rule (3.7). Stage explicit paths. Never force-push main; --force-with-lease only on upgrade/* branches you rebase. Never hard-code cluster values, prune Docker volumes, or put secrets in git, PR bodies or logs.

Order:
0. Security fix D15 per 11.2 item 0 (copy ImprovedDb PR #238), before everything else.
1. Merge P7, P8, P10, P11 exactly per 11.2 item 1 (rebase --onto with the old parent SHAs; Q7 bumps go into P7).
2. Close superseded Dependabot PRs per 11.2 item 2, rechecking each.
3. P12.1, P12.2, P12.3, P12.5 (P12.4 stays skipped).
4. P13a-P13d in order (P13.0-P13.11): the before/after --list-tasks proof in P13.2; set the repository variables before opening P13b.
5. P13.12: when P13a-P13d are merged, send the operator one message, "node-demo: ready for you", pointing to P13.D and the fixed lease 192.168.0.212. A local agent on node-demo does rows 1-2 with the operator, confirms the detected address, and reports its initial CD run URL, SHA and digest. Resume when gh api shows node-demo-books online with label localsinglenode-books. Run rows 3-8 yourself. For row 3, inspect and reuse the matching successful initial deploy evidence; dispatch only if the required deployment has not occurred. Record each run ID before watching, and never re-dispatch because a watcher stopped. For row 4, run Scripts/Test-DeployedSite.ps1 -Address 192.168.0.212 from Windows on the main PC using the verified merged script, and record RESULT: PASS. Record mDNS availability separately; do not require the operator to run this check or reserve the address again.

Deploys: only CD - Deploy LocalSingleNode to node-demo. Never dispatch CD - Deploy LocalCluster or CD - Cloud. Never touch LocalCluster nodes, runners or the deploy lock by hand.

On failure: stop that step, record logs in 11.1, fix it in a PR, resume. If a plan fact is wrong, correct the plan in your next PR (3.0), log it in 11.7, and continue.

Closeout (P13.13): record PR numbers, merge SHAs, run URLs and the deployed digest in 11.1; delete merged upgrade/* branches after recording their SHAs (11.9); set the status line to complete. Report merged PRs, the node-demo URL and results, and anything skipped with reasons. Ask the operator only for MB5-MB7.
```
