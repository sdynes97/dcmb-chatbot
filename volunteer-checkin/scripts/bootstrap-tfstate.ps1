# Run once before the first `terraform init` to create the remote state backend
# and write infra/backend.hcl. Requires: az CLI logged in.
param(
    [string]$SubscriptionId = "",
    [string]$Location = "eastus",
    [string]$ResourceGroup = "vol-checkin-tfstate-rg",
    # Must be globally unique, 3-24 lowercase letters/digits.
    [string]$StorageAccount = "volcheckintf$((Get-Random -Maximum 99999).ToString('00000'))"
)

$ErrorActionPreference = "Stop"

if (-not $SubscriptionId) {
    $SubscriptionId = (az account show --query id -o tsv)
}
az account set --subscription $SubscriptionId

Write-Host "Bootstrapping Terraform state backend in $SubscriptionId ($Location)..."

az group create --name $ResourceGroup --location $Location --output none
Write-Host "  OK  Resource group:  $ResourceGroup"

az storage account create `
    --name $StorageAccount `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku Standard_LRS `
    --min-tls-version TLS1_2 `
    --allow-blob-public-access false `
    --output none
Write-Host "  OK  Storage account: $StorageAccount"

az storage container create `
    --name tfstate `
    --account-name $StorageAccount `
    --auth-mode login `
    --output none
Write-Host "  OK  Container:       tfstate"

$backend = Join-Path $PSScriptRoot "..\infra\backend.hcl"
@"
resource_group_name  = "$ResourceGroup"
storage_account_name = "$StorageAccount"
container_name       = "tfstate"
key                  = "volunteer-checkin.tfstate"
"@ | Set-Content -Path $backend -Encoding utf8
Write-Host "  OK  Wrote infra/backend.hcl"

Write-Host ""
Write-Host "Next:"
Write-Host "  cd infra; terraform init -backend-config=backend.hcl"
Write-Host "Add these GitHub secrets if you deploy with Actions:"
Write-Host "  TFSTATE_RESOURCE_GROUP  = $ResourceGroup"
Write-Host "  TFSTATE_STORAGE_ACCOUNT = $StorageAccount"
