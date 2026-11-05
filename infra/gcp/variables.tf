variable "project_id" {
  type        = string
  description = "Existing project with billing enabled."
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Use an actual Google Cloud project ID."
  }
}
variable "region" {
  type    = string
  default = "asia-southeast1"
}
variable "zone" {
  type    = string
  default = "asia-southeast1-a"
}
variable "enable_public_lb" {
  type        = bool
  default     = false
  description = "Enable after NodePort 30080 works on both workers."
}
variable "web_source_ranges" {
  type    = list(string)
  default = ["0.0.0.0/0"]
  validation {
    condition     = length(var.web_source_ranges) > 0 && alltrue([for c in var.web_source_ranges : can(cidrnetmask(c))])
    error_message = "Provide one or more IPv4 CIDRs."
  }
}
variable "ssh_members" {
  type        = set(string)
  default     = []
  description = "Optional IAM members such as user:alice@example.com, with project-scoped OS Admin Login."
}
variable "os_image" {
  type        = string
  default     = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
  description = "Image family initially; pin an exact image self-link for later builds."
}
variable "control_plane_machine_type" {
  type    = string
  default = "e2-standard-2"
}
variable "worker_machine_type" {
  type    = string
  default = "e2-standard-2"
}
