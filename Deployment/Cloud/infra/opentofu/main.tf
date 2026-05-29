resource "hcloud_ssh_key" "deploy" {
  name       = "${var.project_name}-deploy"
  public_key = trimspace(file(pathexpand(var.ssh_public_key_path)))
  labels     = local.common_labels
}

resource "hcloud_network" "private" {
  name     = "${var.project_name}-private"
  ip_range = var.private_network_cidr
  labels   = local.common_labels
}

resource "hcloud_network_subnet" "private" {
  network_id   = hcloud_network.private.id
  type         = "cloud"
  network_zone = var.network_zone
  ip_range     = var.private_network_cidr
}

resource "hcloud_server" "nodes" {
  for_each = local.server_specs

  name        = each.key
  image       = var.image
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.deploy.id]
  labels      = merge(local.common_labels, { role = each.value.role })
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    ssh_public_key = trimspace(file(pathexpand(var.ssh_public_key_path)))
  })

  public_net {
    ipv4_enabled = var.public_ipv4_enabled
    ipv6_enabled = var.public_ipv6_enabled
  }

  network {
    network_id = hcloud_network.private.id
    ip         = each.value.private_ip
  }

  firewall_ids = each.key == "cloud-main" ? [
    hcloud_firewall.main_public.id,
    hcloud_firewall.temporary_ssh.id,
    ] : [
    hcloud_firewall.no_public_inbound.id,
  ]

  depends_on = [hcloud_network_subnet.private]
}
