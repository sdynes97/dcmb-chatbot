# Davenport Central Marching Band Info Bot

A chatbot for DCMB parents to get real-time schedule info, call times, bus drop-off locations, and director ETA updates — via SMS (Telnyx) or the web chat interface (GitHub Pages).

**Monthly cost: ~$2** (Telnyx $1.50 + Claude Haiku ~$0.50 + Azure ~$0.03)

---

## Architecture

```
Parent (SMS) → Telnyx webhook → Azure Functions → Claude Haiku → SMS reply
Parent (web) → GitHub Pages  → Azure Functions → Claude Haiku → chat response
Director     → SMS or admin.html → Azure Functions → Table Storage (ETA)
```

- **Backend:** Python, Azure Functions (consumption plan — free tier)
- **AI:** Claude claude-haiku-4-5 (Anthropic)
- **SMS:** Telnyx
- **Frontend:** Vanilla JS, GitHub Pages
- **Database:** Azure Table Storage

---

## Setup

### 1. Azure resources

Create these in the [Azure Portal](https://portal.azure.com):

1. **Resource group:** `dcmb-chatbot-rg`
2. **Storage account** (LRS, Standard): `dcmbchatbotstorage`
3. **Function App** (Python 3.12, consumption plan): `dcmb-chatbot-func`
   - Set all environment variables (see below) in **Configuration → Application settings**

### 2. Environment variables

Copy `backend/local.settings.json.example` → `backend/local.settings.json` and fill in:

| Variable | Where to get it |
|---|---|
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Portal → Storage account → Access keys |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `TELNYX_API_KEY` | Telnyx Portal → API Keys |
| `TELNYX_PUBLIC_KEY` | Telnyx Portal → Webhooks → Ed25519 public key |
| `TELNYX_PHONE_NUMBER` | E.164 format, e.g. `+15631234567` |
| `ADMIN_API_KEY` | Generate a random string (e.g. `openssl rand -hex 32`) |
| `DIRECTOR_PHONE` | Director's cell number in E.164 format |
| `FRONTEND_ORIGIN` | Your GitHub Pages URL, e.g. `https://yourusername.github.io` |

### 3. Telnyx webhook

In the Telnyx Portal, set your phone number's inbound webhook URL to:
```
https://dcmb-chatbot-func.azurewebsites.net/api/sms
```

### 4. Seed schedule data

Edit `data/schedule_seed.json` with the real season schedule, then run:

```bash
cd backend
pip install -r requirements.txt
python ../scripts/seed_table.py
```

### 5. GitHub Secrets

Add these secrets in GitHub → Settings → Secrets → Actions:

| Secret | Value |
|---|---|
| `AZURE_CREDENTIALS` | Service principal JSON (see below) |
| `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` | Download from Azure Portal → Function App → Get publish profile |
| `AZURE_STORAGE_CONNECTION_STRING` | Same as local |
| `AZURE_FUNCTION_BASE_URL` | `https://dcmb-chatbot-func.azurewebsites.net` |
| `TELNYX_API_KEY` | Same as local |
| `TELNYX_PUBLIC_KEY` | Same as local |
| `TELNYX_PHONE_NUMBER` | Same as local |
| `TELNYX_DISPLAY_NUMBER` | Human-readable, e.g. `(563) 555-0100` |
| `ANTHROPIC_API_KEY` | Same as local |
| `ADMIN_API_KEY` | Same as local |
| `DIRECTOR_PHONE` | Same as local |
| `FRONTEND_ORIGIN` | GitHub Pages URL |

**Create the service principal:**
```powershell
az ad sp create-for-rbac --name "dcmb-chatbot-deploy" `
  --role contributor `
  --scopes /subscriptions/{subscription-id}/resourceGroups/dcmb-chatbot-rg `
  --sdk-auth
```
Paste the full JSON output as the `AZURE_CREDENTIALS` secret.

### 6. Provision Azure infrastructure with Terraform

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

`terraform output telnyx_webhook_url` gives you the URL to paste into the Telnyx portal.

### 7. GitHub Pages

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

A status bar item shows `[Azurite Table Service]` when it's running. That's all you need.

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

**5. Start the Functions host — open a new terminal tab**
```powershell
cd backend
func start
```

Frontend is plain HTML — open `frontend/index.html` in a browser or use the VS Code Live Server extension.

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

2. **SMS:** Text the bot number from the registered director phone. The message is saved as the current ETA. Example: `"Leaving Lincoln now, home by 10:30pm"`

3. **Manual web form:** On `admin.html`, expand *"Or post a manual update…"* and type a message.

Parents can ask the bot: *"When are the buses back?"* or *"What's the ETA?"*

---

## Updating the schedule

Use `admin.html` or edit `data/schedule_seed.json` and re-run the seed script.
