resource "google_compute_instance_group" "workers" {
  count     = var.enable_public_lb ? 1 : 0
  name      = "nt132-workers"
  zone      = var.zone
  instances = [google_compute_instance.node["wk-01"].self_link, google_compute_instance.node["wk-02"].self_link]
}
resource "google_compute_address" "web" {
  count  = var.enable_public_lb ? 1 : 0
  name   = "nt132-web-ip"
  region = var.region
}
resource "google_compute_region_health_check" "web" {
  count  = var.enable_public_lb ? 1 : 0
  name   = "nt132-web-hc"
  region = var.region
  tcp_health_check { port = 30080 }
}
resource "google_compute_region_backend_service" "web" {
  count                 = var.enable_public_lb ? 1 : 0
  name                  = "nt132-web-backend"
  region                = var.region
  protocol              = "TCP"
  load_balancing_scheme = "EXTERNAL"
  health_checks         = [google_compute_region_health_check.web[0].id]
  backend { group = google_compute_instance_group.workers[0].id }
}
resource "google_compute_forwarding_rule" "web" {
  count                 = var.enable_public_lb ? 1 : 0
  name                  = "nt132-web-forward"
  region                = var.region
  load_balancing_scheme = "EXTERNAL"
  ip_protocol           = "TCP"
  ip_address            = google_compute_address.web[0].address
  ports                 = ["30080"]
  backend_service       = google_compute_region_backend_service.web[0].id
}
resource "google_compute_firewall" "web" {
  count         = var.enable_public_lb ? 1 : 0
  name          = "nt132-public-web"
  network       = google_compute_network.lab.id
  source_ranges = var.web_source_ranges
  target_tags   = ["nt132-worker"]
  allow {
    protocol = "tcp"
    ports    = ["30080"]
  }
}
resource "google_compute_firewall" "health" {
  count         = var.enable_public_lb ? 1 : 0
  name          = "nt132-web-probes"
  network       = google_compute_network.lab.id
  source_ranges = ["35.191.0.0/16", "209.85.152.0/22", "209.85.204.0/22"]
  target_tags   = ["nt132-worker"]
  allow {
    protocol = "tcp"
    ports    = ["30080"]
  }
}
