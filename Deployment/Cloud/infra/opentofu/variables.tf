variable "project_name" {
  type        = string
  description = "Short deployment identity used for resource labels and firewall names."

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,31}$", var.project_name))
    error_message = "project_name must be lowercase, start with a letter, and contain only letters, numbers, or hyphens."
  }
}

variable "location" {
  type        = string
  description = "Hetzner location for all servers."
}

variable "network_zone" {
  type        = string
  description = "Hetzner private network zone."
}

variable "server_type" {
  type        = string
  description = "Hetzner server type for all v1 nodes."
}

variable "image" {
  type        = string
  description = "Server image name."
}

variable "ssh_public_key_path" {
  type        = string
  description = "Path to the deploy SSH public key."
}

variable "public_ipv4_enabled" {
  type        = bool
  description = "Enable public IPv4 on all nodes for outbound package and image access."
}

variable "public_ipv6_enabled" {
  type        = bool
  description = "Enable public IPv6 on all nodes for outbound package and image access."
}

variable "admin_ssh_cidrs" {
  type        = list(string)
  description = "Public CIDRs allowed to SSH to cloud-main outside the temporary GitHub CD rule."

  validation {
    condition     = length(var.admin_ssh_cidrs) > 0 && alltrue([for cidr in var.admin_ssh_cidrs : can(cidrhost(cidr, 0))])
    error_message = "admin_ssh_cidrs must contain at least one valid CIDR, for example 203.0.113.10/32."
  }
}

variable "private_network_cidr" {
  type        = string
  description = "Private network CIDR for the Cloud deployment."

  validation {
    condition     = can(cidrhost(var.private_network_cidr, 0))
    error_message = "private_network_cidr must be a valid CIDR."
  }
}

variable "cloud_main_private_ip" {
  type        = string
  description = "Private IP for cloud-main."
}

variable "cloud_app1_private_ip" {
  type        = string
  description = "Private IP for cloud-app1."
}

variable "cloud_app2_private_ip" {
  type        = string
  description = "Private IP for cloud-app2."
}

variable "cloud_db_private_ip" {
  type        = string
  description = "Private IP for cloud-db."
}
