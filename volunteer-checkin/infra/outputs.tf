output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "function_app_name" {
  value = azurerm_linux_function_app.main.name
}

output "api_base_url" {
  description = "Goes into frontend/js/config.js as API_BASE_URL"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}/api"
}

output "storage_account_name" {
  value = azurerm_storage_account.main.name
}

output "kiosk_url" {
  description = "Kiosk page (admin page is admin.html under the same URL)"
  value       = azurerm_storage_account.main.primary_web_endpoint
}
