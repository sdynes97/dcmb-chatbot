locals {
  # Sanitised prefix: lowercase, max 20 chars (storage account name limit is 24)
  prefix = lower(replace(var.app_name, "-", ""))

  # Resource names
  resource_group_name     = "${var.app_name}-rg"
  storage_account_name    = substr("${local.prefix}${var.environment}", 0, 24)
  function_app_name       = "${var.app_name}-func"
  app_service_plan_name   = "${var.app_name}-plan"
  app_insights_name       = "${var.app_name}-insights"
  log_analytics_name      = "${var.app_name}-logs"

  common_tags = {
    project     = "dcmb-chatbot"
    environment = var.environment
    managed_by  = "terraform"
  }
}
