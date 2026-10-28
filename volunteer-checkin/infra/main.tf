# Volunteer check-in — standalone Azure resources
#   - Storage account: Table Storage for check-ins + static website for the kiosk/admin pages
#   - Function App (Linux consumption, Python) for the API
#   - Application Insights for logs

locals {
  prefix = lower(replace(var.app_name, "-", ""))
  tags = {
    project    = var.app_name
    managed_by = "terraform"
  }
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

resource "azurerm_resource_group" "main" {
  name     = "${var.app_name}-rg"
  location = var.location
  tags     = local.tags
}

# ── Storage: data + static website ───────────────────────────────────────────

resource "azurerm_storage_account" "main" {
  name                            = substr("${local.prefix}${random_string.suffix.result}", 0, 24)
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  tags                            = local.tags
}

resource "azurerm_storage_account_static_website" "main" {
  storage_account_id = azurerm_storage_account.main.id
  index_document     = "index.html"
}

resource "azurerm_storage_table" "checkins" {
  name                 = "volunteercheckins"
  storage_account_name = azurerm_storage_account.main.name
}

# ── Monitoring ───────────────────────────────────────────────────────────────

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.app_name}-logs"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_application_insights" "main" {
  name                = "${var.app_name}-insights"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = local.tags
}

# ── Function App ─────────────────────────────────────────────────────────────

resource "azurerm_service_plan" "main" {
  name                = "${var.app_name}-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "Y1" # Consumption — free tier covers kiosk volumes
  tags                = local.tags
}

resource "azurerm_linux_function_app" "main" {
  name                       = "${var.app_name}-${random_string.suffix.result}-func"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  service_plan_id            = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key
  https_only                 = true
  tags                       = local.tags

  site_config {
    application_stack {
      python_version = "3.12"
    }

    cors {
      allowed_origins = concat(
        [trimsuffix(azurerm_storage_account.main.primary_web_endpoint, "/")],
        var.extra_cors_origins,
      )
      support_credentials = false
    }

    application_insights_connection_string = azurerm_application_insights.main.connection_string
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"        = "python"
    "AZURE_STORAGE_CONNECTION_STRING" = azurerm_storage_account.main.primary_connection_string
    "TABLE_NAME"                      = azurerm_storage_table.checkins.name
    "KIOSK_TIMEZONE"                  = var.kiosk_timezone
    "ADMIN_API_KEY"                   = var.admin_api_key
    "KIOSK_API_KEY"                   = var.kiosk_api_key
  }

  lifecycle {
    ignore_changes = [app_settings["WEBSITE_RUN_FROM_PACKAGE"]]
  }
}
