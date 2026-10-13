# Deploy LocalSingleNode

LocalSingleNode runs on a native Linux Mint PC. It serves HTTP on the LAN by default. The app, PostgreSQL and Redis ports bind to loopback. Do not expose the LAN HTTP listener to the internet. Windows and WSL can act as controllers; they cannot host this target. Observability is unsupported; keep `observability_enabled: false`. Use [Public setup](PublicSetup.md) for HTTPS.

## Routes

- Set up or resume this current node: follow [AgentSetup](AgentSetup.md). It owns the authorization check, setup state machine, operator-run root command and stop conditions.
- Pair the main PC with an existing node: follow [Controller SSH](ControllerSsh.md).
- Check a candidate without changing the node: follow [readiness](Readiness.md).
- Publish an existing LAN app through HTTPS: follow [Public setup](PublicSetup.md).
- Add or select another app on this node: follow [application instances](ApplicationInstances.md).
- Release, diagnose, maintain, back up, restore, roll back or remove an app: use [operations](Operations.md).
- Change the target's checked settings in [all.yml](inventory/group_vars/all.yml). Use the [shared release contract](../Common/ReleaseContract.md) for image, migration and CI provenance rules.

## First setup and verification

Use `AgentSetup.md` only when the operator explicitly asks to set up the current native PC. It explains the setup state machine and gives the operator one complete root command to run. Do not bootstrap an existing node again.

After setup, complete the [controller SSH handoff](ControllerSsh.md) and follow AgentSetup's independent LAN acceptance step. To add public HTTPS, complete the separate [Public setup](PublicSetup.md) route. Do not treat LAN HTTP as public deployment.

For an existing node, run the read-only doctor from its repository checkout and follow [operations](Operations.md#diagnose-a-running-node):

```bash
bash ./Deployment/LocalSingleNode/Scripts/doctor.sh --json
```

## Backups and recovery

Use [operations](Operations.md#backups-and-recovery). Manual restore creates a replacement database; it never overwrites the live database.

## Remove the app

Use [operations](Operations.md#remove-an-application). Preserve shared services, other apps and data volumes.
