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

variable "telnyx_api_key" {
  description = "Telnyx API key for SMS"
  type        = string
  sensitive   = true
}

variable "telnyx_public_key" {
  description = "Telnyx Ed25519 public key for webhook validation"
  type        = string
  sensitive   = true
}

variable "telnyx_phone_number" {
  description = "Telnyx phone number in E.164 format, e.g. +15631234567"
  type        = string
}

variable "telnyx_display_number" {
  description = "Human-readable Telnyx number shown in the web UI, e.g. (563) 555-0100"
  type        = string
}

variable "admin_api_key" {
  description = "Admin API key for the schedule management endpoints"
  type        = string
  sensitive   = true
}

variable "director_phone" {
  description = "Band director's phone in E.164 format — texts from this number become ETA updates"
  type        = string
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
