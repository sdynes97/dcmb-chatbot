variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus"
}

variable "app_name" {
  description = "Short name used as the resource name prefix"
  type        = string
  default     = "vol-checkin"
}

variable "extra_cors_origins" {
  description = "Other origins allowed to call the API (e.g. an app that hosts its own copy of the kiosk page)"
  type        = list(string)
  default     = []
}

variable "kiosk_timezone" {
  description = "IANA timezone used for the check-in date/time columns"
  type        = string
  default     = "America/Chicago"
}

# ── Secrets passed in at deploy time ────────────────────────────────────────

variable "admin_api_key" {
  description = "Key for the admin page (roster, activities, export)"
  type        = string
  sensitive   = true
}

variable "kiosk_api_key" {
  description = "Optional key the kiosk sends as X-Kiosk-Key. Empty = kiosk endpoints are open."
  type        = string
  sensitive   = true
  default     = ""
}
