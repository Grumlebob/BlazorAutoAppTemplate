locals {
  common_labels = {
    app        = var.project_name
    deployment = "cloud"
    managed_by = "opentofu"
  }

  server_specs = {
    cloud-main = {
      role       = "ingress"
      private_ip = var.cloud_main_private_ip
    }
    cloud-app1 = {
      role       = "app"
      private_ip = var.cloud_app1_private_ip
    }
    cloud-app2 = {
      role       = "app"
      private_ip = var.cloud_app2_private_ip
    }
    cloud-db = {
      role       = "data"
      private_ip = var.cloud_db_private_ip
    }
  }
}
