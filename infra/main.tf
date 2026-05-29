# ── Resource Group ───────────────────────────────────────────────────────────

resource "azurerm_resource_group" "main" {
  name     = local.resource_group_name
  location = var.location
  tags     = local.common_tags
}

# ── Storage Account ──────────────────────────────────────────────────────────
# Serves two purposes:
#   1. Azure Functions runtime storage (required)
#   2. Azure Table Storage for schedule data and ETA updates

resource "azurerm_storage_account" "main" {
  name                     = local.storage_account_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  # Disable public blob access — tables are not blobs but keep baseline hardened
  allow_nested_items_to_be_public = false

  tags = local.common_tags
}

resource "azurerm_storage_table" "schedule" {
  name                 = "bandschedule"
  storage_account_name = azurerm_storage_account.main.name
}

# ── Log Analytics + Application Insights ─────────────────────────────────────

resource "azurerm_log_analytics_workspace" "main" {
  name                = local.log_analytics_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

resource "azurerm_application_insights" "main" {
  name                = local.app_insights_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = local.common_tags
}

# ── App Service Plan (Consumption — Y1) ──────────────────────────────────────

resource "azurerm_service_plan" "main" {
  name                = local.app_service_plan_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "Y1"  # Consumption plan — free tier
  tags                = local.common_tags
}

# ── Azure Function App ────────────────────────────────────────────────────────

resource "azurerm_linux_function_app" "main" {
  name                       = local.function_app_name
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  service_plan_id            = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key
  https_only                 = true
  tags                       = local.common_tags

  site_config {
    application_stack {
      python_version = "3.12"
    }

    cors {
      allowed_origins     = [var.frontend_origin]
      support_credentials = false
    }

    application_insights_connection_string = azurerm_application_insights.main.connection_string
    application_insights_key               = azurerm_application_insights.main.instrumentation_key
  }

  app_settings = {
    # Azure Functions runtime
    "FUNCTIONS_WORKER_RUNTIME"        = "python"
    "AzureWebJobsStorage"             = azurerm_storage_account.main.primary_connection_string
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string

    # Application config
    "AZURE_STORAGE_CONNECTION_STRING" = azurerm_storage_account.main.primary_connection_string
    "TABLE_STORAGE_TABLE_NAME"        = azurerm_storage_table.schedule.name
    "FRONTEND_ORIGIN"                 = var.frontend_origin

    # Secrets
    "ANTHROPIC_API_KEY"   = var.anthropic_api_key
    "ADMIN_API_KEY"       = var.admin_api_key
    "SCHOOL_LAT"          = var.school_lat
    "SCHOOL_LNG"          = var.school_lng
    "AVG_SPEED_MPH"       = var.avg_speed_mph
  }

  lifecycle {
    # Prevent Terraform from clobbering app settings written by the Functions runtime
    ignore_changes = [
      app_settings["WEBSITE_RUN_FROM_PACKAGE"],
    ]
  }
}
