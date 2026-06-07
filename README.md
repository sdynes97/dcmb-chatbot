# Davenport Central Marching Band Info Bot

A mobile-friendly web chatbot for DCMB parents to get real-time schedule info, call times, bus drop-off locations, and director ETA updates — hosted free on GitHub Pages.

**Monthly cost: ~$0.50** (Claude Haiku ~$0.50 + Azure free tier)

---

## Architecture

```
Parent (web/mobile) → GitHub Pages → Azure Functions → Claude Haiku → chat response
Director            → admin.html (web form or live GPS) → Azure Functions → Table Storage (ETA)
```

- **Backend:** Python, Azure Functions (consumption plan — free tier)
- **AI:** Claude claude-haiku-4-5 (Anthropic)
- **Frontend:** Vanilla JS, GitHub Pages (responsive / mobile-first)
- **Database:** Azure Table Storage

---

## Setup

### 1. Azure resources

Terraform will create the app resource group and app resources for you. Do not pre-create the app resource group, storage account, or Function App unless you plan to import them into Terraform state.

The only required pre-provisioning is the Terraform remote state backend:

- Resource group: `dcmb-tfstate-rg`
- Storage account: `dcmbtfstate`
- Container: `tfstate`

Use the bootstrap script instead of manually creating the backend storage resources:

```powershell
az login
.\scripts\bootstrap-tfstate.ps1
```

If you already created `dcmb-chatbot-rg` manually, import it before running `terraform plan`:

```powershell
cd infra
terraform init
terraform import azurerm_resource_group.main /subscriptions/<subscription-id>/resourceGroups/dcmb-chatbot-rg
```

If you also manually created the app storage account, import that too:

```powershell
terraform import azurerm_storage_account.main /subscriptions/<subscription-id>/resourceGroups/dcmb-chatbot-rg/providers/Microsoft.Storage/storageAccounts/dcmbchatbotstorage
```

### 2. Environment variables

Copy `backend/local.settings.json.example` → `backend/local.settings.json` and fill in:

| Variable | Where to get it |
|---|---|
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Portal → Storage account → Access keys |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `ADMIN_API_KEY` | Generate a random string (e.g. `openssl rand -hex 32`) |
| `FRONTEND_ORIGIN` | Your GitHub Pages URL, e.g. `https://yourusername.github.io` |

### 3. Seed schedule data

Edit `data/schedule_seed.json` with the real season schedule, then run:

```bash
cd backend
pip install -r requirements.txt
python ../scripts/seed_table.py
```

### 4. GitHub Secrets

Add these secrets in GitHub → Settings → Secrets → Actions:

| Secret | Value |
|---|---|
| `AZURE_CREDENTIALS` | Service principal JSON (see below) |
| `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` | Download from Azure Portal → Function App → Get publish profile |
| `ANTHROPIC_API_KEY` | Same as local |
| `ADMIN_API_KEY` | Same as local |
| `FRONTEND_ORIGIN` | GitHub Pages URL |

**Create the service principal:**
```powershell
az ad sp create-for-rbac --name "dcmb-chatbot-deploy" `
  --role contributor `
  --scopes /subscriptions/{subscription-id}/resourceGroups/dcmb-chatbot-rg /subscriptions/{subscription-id}/resourceGroups/dcmb-tfstate-rg `
  --sdk-auth
```
Paste the full JSON output as the `AZURE_CREDENTIALS` secret.

> Note: Terraform remote state is stored in a separate resource group and storage account (`dcmb-tfstate-rg` / `dcmbtfstate`). The service principal must have access to both the app resource group and the backend state resource group.

If you already created the SP with only the app RG scope, grant it access to the backend state RG as well:
```powershell
az role assignment create `
  --assignee <service-principal-appId-or-objectId> `
  --role "Storage Blob Data Contributor" `
  --scope /subscriptions/{subscription-id}/resourceGroups/dcmb-tfstate-rg
```

### 5. Provision Azure infrastructure with Terraform

**One-time: bootstrap the Terraform remote state bucket**
```powershell
az login
.\scripts\bootstrap-tfstate.ps1
```

**Fill in your values**
```powershell
Copy-Item infra\terraform.tfvars.example infra\terraform.tfvars
notepad infra\terraform.tfvars
```

**Init, plan, and apply**
```powershell
cd infra
terraform init
terraform plan
terraform apply
```

`terraform output function_app_url` gives you the backend URL (also injected into the frontend automatically by the deploy workflow).

### 6. GitHub Pages

In the repo → Settings → Pages → Source: **Deploy from branch** → `gh-pages` / `/ (root)`.

---

## Local development

Open a PowerShell terminal in the repo root.

**1. Install Azure Functions Core Tools (once)**
```powershell
winget install Microsoft.Azure.FunctionsCoreTools
```
Restart your terminal after install so `func` is on your PATH.

**2. Start Azurite (local Table Storage emulator)**

Azurite is built into the **VS Code Azurite extension** — the easiest option, no extra install:
1. Open VS Code → Extensions → search **Azurite** (publisher: Microsoft) → Install
2. Open the Command Palette (`Ctrl+Shift+P`) → **Azurite: Start**

⚠️ Start **all three** Azurite services (Blob `10000`, Queue `10001`, Table `10002`), not just Table. The Functions host's own `AzureWebJobsStorage` uses Blob + Queue — if those aren't running you'll see `azure.functions.webjobs.storage … Unhealthy` (timeout). Your app data lives in the Table service. The VS Code **Azurite: Start** command launches all three; from a terminal, run `azurite` with no args (avoid `azurite-table`, which starts only the table service).

The connection string `UseDevelopmentStorage=true` (already set in `local.settings.json.example`) automatically points both the Functions host and the SDK at Azurite's local endpoints — no account name or key needed.

**3. Install Python dependencies**
```powershell
cd backend
pip install -r requirements-dev.txt
```

**4. Copy and fill in local settings**
```powershell
Copy-Item local.settings.json.example local.settings.json
notepad local.settings.json
```

**5. Create the `bandschedule` table / seed data (optional)**

You do **not** need to create the table by hand. The app creates it on first
access — `_get_table_client()` in `schedule_service.py` and `location_service.py`
calls `create_table()` idempotently, so the first chat query, admin write, or ETA
update auto-creates an empty `bandschedule` table in Azurite.

To start with real data instead of an empty table, run the seed script (it also
creates the table):
```powershell
cd backend
python ../scripts/seed_table.py
```

**6. Start the Functions host — open a new terminal tab**
```powershell
cd backend
func start
```

Frontend is plain HTML — open `frontend/index.html` in a browser or use the VS Code Live Server extension.

> **Note:** `pytest` does not use Azurite — the test suite mocks the table client
> entirely (see `tests/conftest.py`), so you only need Azurite running to exercise
> the app end-to-end via `func start`.

---

## Running tests

```powershell
cd backend
python -m pytest tests/ -v
```

---

## Director ETA updates

The director has three ways to update the parent-facing ETA:

1. **Live GPS tracking (recommended):** Open `admin.html` on your phone, sign in, and tap **Start Live Tracking**. Your phone's GPS sends your location to the backend every 30 seconds. The ETA auto-calculates as *"Bus is 8.2 mi away, ETA ~10:43 PM"* and updates continuously until you tap Stop.

2. **Manual web form:** On `admin.html`, expand *"Or post a manual update…"* and type a message.

Parents can ask the bot: *"When are the buses back?"* or *"What's the ETA?"*

---

## Updating the schedule

Use `admin.html` or edit `data/schedule_seed.json` and re-run the seed script.
