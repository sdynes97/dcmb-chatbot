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
```bash
az ad sp create-for-rbac --name "dcmb-chatbot-deploy" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/dcmb-chatbot-rg \
  --sdk-auth
```
Paste the full JSON output as the `AZURE_CREDENTIALS` secret.

### 6. GitHub Pages

In the repo → Settings → Pages → Source: **Deploy from branch** → `gh-pages` / `/ (root)`.

---

## Local development

```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Install Azurite (local Table Storage emulator)
npm install -g azurite

# Start Azurite in a separate terminal
azurite --silent --location /tmp/azurite

# Install Python dependencies
cd backend
pip install -r requirements-dev.txt

# Copy and fill in local settings
cp local.settings.json.example local.settings.json

# Start the Functions host
func start
```

Frontend is plain HTML — open `frontend/index.html` in a browser or use Live Server.

---

## Running tests

```bash
cd backend
pytest tests/ -v
```

---

## Director ETA updates

The band director can update the parent-facing ETA in two ways:

1. **SMS:** Text the bot number from the registered director phone. The message is automatically saved as the current ETA. Example: `"Leaving Lincoln now, home by 10:30pm"`

2. **Web form:** Go to `https://yourusername.github.io/admin.html`, enter the admin API key, and fill out the ETA form.

Parents can ask the bot: *"When are the buses back?"* or *"What's the ETA?"*

---

## Updating the schedule

Use `admin.html` or edit `data/schedule_seed.json` and re-run the seed script.
