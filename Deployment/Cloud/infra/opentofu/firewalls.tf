resource "hcloud_firewall" "main_public" {
  name   = "${var.project_name}-main-public"
  labels = merge(local.common_labels, { role = "ingress" })

  rule {
    direction   = "in"
    protocol    = "tcp"
    port        = "22"
    source_ips  = var.admin_ssh_cidrs
    description = "Admin SSH to cloud-main"
  }
}

resource "hcloud_firewall" "temporary_ssh" {
  name   = "${var.project_name}-temporary-ssh"
  labels = merge(local.common_labels, { role = "temporary-ssh" })

  lifecycle {
    ignore_changes = [rule]
  }
}

resource "hcloud_firewall" "no_public_inbound" {
  name   = "${var.project_name}-no-public-inbound"
  labels = merge(local.common_labels, { role = "private-service" })
}
