locals {
  nodes = {
    cp-01 = { ip = "10.20.0.10", role = "cp", disk = 30 }
    wk-01 = { ip = "10.20.0.11", role = "worker", disk = 40 }
    wk-02 = { ip = "10.20.0.12", role = "worker", disk = 40 }
  }
  apis      = toset(["compute.googleapis.com", "iap.googleapis.com", "oslogin.googleapis.com"])
  ssh_roles = toset(["roles/compute.viewer", "roles/compute.osAdminLogin", "roles/iap.tunnelResourceAccessor"])
  grants = { for pair in setproduct(var.ssh_members, local.ssh_roles) :
    "${pair[0]}|${pair[1]}" => { member = pair[0], role = pair[1] }
  }
}
resource "google_project_service" "api" {
  for_each           = local.apis
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}
resource "google_project_iam_member" "ssh" {
  for_each = local.grants
  project  = var.project_id
  member   = each.value.member
  role     = each.value.role
}
resource "google_compute_network" "lab" {
  name                    = "nt132-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.api]
}
resource "google_compute_subnetwork" "nodes" {
  name          = "nt132-subnet"
  network       = google_compute_network.lab.id
  region        = var.region
  ip_cidr_range = "10.20.0.0/24"
}
resource "google_compute_address" "node" {
  for_each     = local.nodes
  name         = "nt132-${each.key}-ip"
  region       = var.region
  address_type = "INTERNAL"
  subnetwork   = google_compute_subnetwork.nodes.id
  address      = each.value.ip
}
resource "google_compute_instance" "node" {
  for_each       = local.nodes
  name           = each.key
  zone           = var.zone
  machine_type   = each.value.role == "cp" ? var.control_plane_machine_type : var.worker_machine_type
  can_ip_forward = true
  tags           = ["nt132-node", "nt132-${each.value.role}"]
  labels         = { project = "nt132", role = each.value.role }
  boot_disk {
    auto_delete = true
    initialize_params {
      image = var.os_image
      size  = each.value.disk
      type  = "pd-balanced"
    }
  }
  network_interface {
    subnetwork = google_compute_subnetwork.nodes.id
    network_ip = google_compute_address.node[each.key].address
    # Egress uses external IP; inbound SSH only uses IAP.
    access_config {}
  }
  metadata = {
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
  }
  shielded_instance_config {
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }
  lifecycle {
    precondition {
      condition     = startswith(var.zone, "${var.region}-")
      error_message = "zone must belong to region."
    }
  }
}
resource "google_compute_firewall" "iap" {
  name          = "nt132-iap-ssh"
  network       = google_compute_network.lab.id
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["nt132-node"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}
resource "google_compute_firewall" "api" {
  name        = "nt132-api"
  network     = google_compute_network.lab.id
  source_tags = ["nt132-node"]
  target_tags = ["nt132-cp"]
  allow {
    protocol = "tcp"
    ports    = ["6443"]
  }
}
resource "google_compute_firewall" "kubelet" {
  name        = "nt132-kubelet"
  network     = google_compute_network.lab.id
  source_tags = ["nt132-cp"]
  target_tags = ["nt132-node"]
  allow {
    protocol = "tcp"
    ports    = ["10250"]
  }
}
resource "google_compute_firewall" "overlay" {
  name        = "nt132-overlay"
  network     = google_compute_network.lab.id
  source_tags = ["nt132-node"]
  target_tags = ["nt132-node"]
  allow {
    protocol = "udp"
    ports    = ["4789"]
  }
  allow {
    protocol = "tcp"
    ports    = ["5473", "30080"]
  }
  allow { protocol = "icmp" }
}
