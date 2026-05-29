variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus"
}

variable "environment" {
  description = "Deployment environment (prod, staging)"
  type        = string
  default     = "prod"
}

variable "app_name" {
  description = "Short application name used as resource name prefix"
  type        = string
  default     = "dcmb-chatbot"
}

# ── Secrets passed in at deploy time (not stored in state) ──────────────────

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude"
  type        = string
  sensitive   = true
}

variable "admin_api_key" {
  description = "Admin API key for the schedule management endpoints"
  type        = string
  sensitive   = true
}

variable "school_lat" {
  description = "School latitude for ETA calculation (Davenport Central default)"
  type        = string
  default     = "41.5236"
}

variable "school_lng" {
  description = "School longitude for ETA calculation (Davenport Central default)"
  type        = string
  default     = "-90.5776"
}

variable "avg_speed_mph" {
  description = "Assumed average bus speed in mph for ETA calculation"
  type        = string
  default     = "35"
}

variable "frontend_origin" {
  description = "GitHub Pages origin for CORS, e.g. https://sdynes97.github.io"
  type        = string
}
