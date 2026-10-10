---
name: setup-local-single-node
description: Set up the current native Linux PC as a LocalSingleNode deployment node only after an explicit operator request for this machine.
---

Use only when the operator explicitly asks to set up this current PC as a deployment node. Mentioning another node from a controller session is not a trigger. Reject Windows and WSL node bootstrap.

Read and follow the repository's `Deployment/LocalSingleNode/AgentSetup.md`. It is the canonical runbook. The operator performs authentication and the one sudo command; the agent never types, stores or requests passwords/tokens and never invokes sudo.
