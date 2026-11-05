mock_provider "google" {}

variables {
  project_id = "nt132-test-project"
}

run "private_bootstrap" {
  command = plan
  assert {
    condition     = length(google_compute_instance.node) == 3
    error_message = "Exactly three nodes are required."
  }
  assert {
    condition     = length(google_compute_forwarding_rule.web) == 0
    error_message = "The public load balancer must be opt-in."
  }
  assert {
    condition     = google_compute_firewall.iap.source_ranges == toset(["35.235.240.0/20"])
    error_message = "SSH must use IAP sources."
  }
}

run "public_application" {
  # Mocked apply resolves instance self-links without contacting Google Cloud.
  command = apply
  variables {
    enable_public_lb  = true
    web_source_ranges = ["203.0.113.10/32"]
  }
  assert {
    condition     = length(google_compute_instance_group.workers[0].instances) == 2
    error_message = "Only the two workers belong to the LB backend."
  }
  assert {
    condition     = google_compute_forwarding_rule.web[0].ports == toset(["30080"])
    error_message = "Frontend port must match the HTTP NodePort."
  }
  assert {
    condition     = google_compute_firewall.web[0].source_ranges == toset(["203.0.113.10/32"])
    error_message = "Caller-provided source ranges must be preserved."
  }
}

run "reject_mismatched_zone" {
  command = plan
  variables {
    zone = "us-central1-a"
  }
  expect_failures = [google_compute_instance.node]
}
