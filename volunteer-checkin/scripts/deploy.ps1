# Deploy everything from your PC: infrastructure, API and web pages.
# Requires: az CLI (logged in), Terraform >= 1.9, infra/backend.hcl and
# infra/terraform.tfvars (see README). Safe to re-run.
param(
    [switch]$SkipInfra
)

$ErrorActionPreference = "Stop"
$root  = Resolve-Path (Join-Path $PSScriptRoot "..")
$infra = Join-Path $root "infra"

Push-Location $infra
try {
    if (-not $SkipInfra) {
        terraform init -backend-config=backend.hcl -input=false
        if ($LASTEXITCODE) { throw "terraform init failed" }
        terraform apply -input=false
        if ($LASTEXITCODE) { throw "terraform apply failed" }
    }
    $rg      = terraform output -raw resource_group_name
    $func    = terraform output -raw function_app_name
    $apiBase = terraform output -raw api_base_url
    $storage = terraform output -raw storage_account_name
    $kiosk   = terraform output -raw kiosk_url
}
finally {
    Pop-Location
}

# ── API (Azure Functions, remote build installs requirements.txt) ────────────
$zip = Join-Path ([IO.Path]::GetTempPath()) "volunteer-checkin-api.zip"
Remove-Item $zip -ErrorAction SilentlyContinue
$backend = Join-Path $root "backend"
$files = Get-ChildItem $backend -Recurse -File | Where-Object {
    $_.FullName -notmatch '[\\/](tests|__pycache__|\.pytest_cache|\.venv)[\\/]' -and
    $_.Name -ne "local.settings.json"
}
Compress-Archive -Path ($files | ForEach-Object FullName) -DestinationPath $zip
# Compress-Archive flattens paths; the backend has no subfolders to preserve.
az functionapp deployment source config-zip `
    --resource-group $rg --name $func --src $zip --build-remote true --output none
if ($LASTEXITCODE) { throw "Function deploy failed" }
Write-Host "  OK  API deployed: $apiBase"

# ── Web pages (storage static website) ───────────────────────────────────────
$site = Join-Path ([IO.Path]::GetTempPath()) "volunteer-checkin-site"
Remove-Item $site -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $root "frontend") $site -Recurse
$config = Join-Path $site "js\config.js"
(Get-Content $config -Raw).Replace("http://localhost:7071/api", $apiBase) | Set-Content $config -NoNewline

az storage blob upload-batch `
    --account-name $storage --auth-mode key `
    --destination '$web' --source $site --overwrite --output none
if ($LASTEXITCODE) { throw "Web upload failed" }

Write-Host ""
Write-Host "Kiosk: $kiosk"
Write-Host "Admin: ${kiosk}admin.html"
