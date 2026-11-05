output "nodes" {
  value = { for name, vm in google_compute_instance.node :
    name => { private_ip = vm.network_interface[0].network_ip, zone = vm.zone }
  }
}
output "web_ip" {
  value = try(google_compute_address.web[0].address, null)
}
output "ssh_control_plane" {
  value = "gcloud compute ssh cp-01 --project=${var.project_id} --zone=${var.zone} --tunnel-through-iap"
}
