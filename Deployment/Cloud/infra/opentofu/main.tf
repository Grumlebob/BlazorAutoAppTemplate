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

resource "hcloud_server" "cloud_main" {
  name        = "cloud-main"
  image       = var.image
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.deploy.id]
  labels      = merge(local.common_labels, { role = local.cloud_main_spec.role })
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    app_name                      = var.project_name
    nat_gateway_enabled           = true
    private_default_route_enabled = false
    private_network_cidr          = var.private_network_cidr
    private_network_gateway_ip    = cidrhost(var.private_network_cidr, 1)
    ssh_public_key                = trimspace(file(pathexpand(var.ssh_public_key_path)))
  })

  public_net {
    ipv4_enabled = var.public_ipv4_enabled
    ipv6_enabled = var.public_ipv6_enabled
  }

  network {
    network_id = hcloud_network.private.id
    ip         = local.cloud_main_spec.private_ip
  }

  firewall_ids = [
    hcloud_firewall.main_public.id,
    hcloud_firewall.temporary_ssh.id,
  ]

  lifecycle {
    ignore_changes = [user_data]
  }

  depends_on = [hcloud_network_subnet.private]
}

resource "hcloud_network_route" "private_default_egress" {
  network_id  = hcloud_network.private.id
  destination = "0.0.0.0/0"
  gateway     = var.cloud_main_private_ip

  depends_on = [hcloud_server.cloud_main]
}

resource "hcloud_server" "private_nodes" {
  for_each = local.private_server_specs

  name        = each.key
  image       = var.image
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.deploy.id]
  labels      = merge(local.common_labels, { role = each.value.role })
  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    app_name                      = var.project_name
    nat_gateway_enabled           = false
    private_default_route_enabled = true
    private_network_cidr          = var.private_network_cidr
    private_network_gateway_ip    = cidrhost(var.private_network_cidr, 1)
    ssh_public_key                = trimspace(file(pathexpand(var.ssh_public_key_path)))
  })

  public_net {
    ipv4_enabled = false
    ipv6_enabled = false
  }

  network {
    network_id = hcloud_network.private.id
    ip         = each.value.private_ip
  }

  firewall_ids = [
    hcloud_firewall.no_public_inbound.id,
  ]

  lifecycle {
    ignore_changes = [user_data]
  }

  depends_on = [hcloud_network_route.private_default_egress]
}

moved {
  from = hcloud_server.nodes["cloud-main"]
  to   = hcloud_server.cloud_main
}

moved {
  from = hcloud_server.nodes["cloud-app1"]
  to   = hcloud_server.private_nodes["cloud-app1"]
}

moved {
  from = hcloud_server.nodes["cloud-app2"]
  to   = hcloud_server.private_nodes["cloud-app2"]
}

moved {
  from = hcloud_server.nodes["cloud-db"]
  to   = hcloud_server.private_nodes["cloud-db"]
}
