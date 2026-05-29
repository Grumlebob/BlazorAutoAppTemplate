# Cloud OpenTofu

This folder will contain the Hetzner Cloud OpenTofu root module.

OpenTofu owns:

- four x86_64 Hetzner servers: `cloud-main`, `cloud-app1`, `cloud-app2`, `cloud-db`.
- private network and server attachments.
- role-specific Hetzner Firewall resources.
- SSH key resource for the `deploy` user.
- cloud-init/user-data for initial access.
- outputs used by Ansible inventory rendering.

Do not commit local state, plan files, or real `.tfvars` files. Commit provider version constraints and the generated dependency lock file once the module is implemented.
