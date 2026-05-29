# Run once before the first `terraform init` to create the remote state backend.
# Requires: az CLI logged in with Contributor on the subscription.
param(
    [string]$SubscriptionId = "",
    [string]$Location = "eastus"
)

$ErrorActionPreference = "Stop"

if (-not $SubscriptionId) {
    $SubscriptionId = (az account show --query id -o tsv)
}

$Rg        = "dcmb-tfstate-rg"
$Sa        = "dcmbtfstate"
$Container = "tfstate"

Write-Host "Bootstrapping Terraform state backend..."
Write-Host "  Subscription: $SubscriptionId"
Write-Host "  Location:     $Location"

az group create --name $Rg --location $Location --output none
Write-Host "  OK  Resource group: $Rg"

az storage account create `
    --name $Sa `
    --resource-group $Rg `
    --location $Location `
    --sku Standard_LRS `
    --min-tls-version TLS1_2 `
    --allow-blob-public-access false `
    --output none
Write-Host "  OK  Storage account: $Sa"

az storage container create `
    --name $Container `
    --account-name $Sa `
    --auth-mode login `
    --output none
Write-Host "  OK  Container: $Container"

Write-Host ""
Write-Host "Backend ready. Now run:"
Write-Host "  cd infra; terraform init"
