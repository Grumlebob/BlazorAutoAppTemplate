output "cloud_main_public_ipv4" {
  value       = hcloud_server.cloud_main.ipv4_address
  description = "Public IPv4 for cloud-main SSH and Cloud CD bastion access."
}

output "cloud_main_private_ip" {
  value       = var.cloud_main_private_ip
  description = "Private IP for cloud-main."
}

output "cloud_app1_private_ip" {
  value       = var.cloud_app1_private_ip
  description = "Private IP for cloud-app1."
}

output "cloud_app2_private_ip" {
  value       = var.cloud_app2_private_ip
  description = "Private IP for cloud-app2."
}

output "cloud_db_private_ip" {
  value       = var.cloud_db_private_ip
  description = "Private IP for cloud-db."
}

output "cloud_temp_ssh_firewall_id" {
  value       = hcloud_firewall.temporary_ssh.id
  description = "Hetzner firewall ID used by CD - Cloud for temporary SSH access."
}
