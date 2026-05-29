output "resource_group_name" {
  description = "Name of the Azure resource group"
  value       = azurerm_resource_group.main.name
}

output "function_app_name" {
  description = "Name of the Azure Function App"
  value       = azurerm_linux_function_app.main.name
}

output "function_app_url" {
  description = "Base URL of the Function App (used as AZURE_FUNCTION_BASE_URL in GitHub Secrets)"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}"
}

output "function_app_hostname" {
  description = "Hostname of the Function App"
  value       = azurerm_linux_function_app.main.default_hostname
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_connection_string" {
  description = "Connection string for Azure Table Storage (add to GitHub Secrets as AZURE_STORAGE_CONNECTION_STRING)"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

output "telnyx_webhook_url" {
  description = "Set this as the inbound webhook URL in the Telnyx portal for your phone number"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}/api/sms"
}
