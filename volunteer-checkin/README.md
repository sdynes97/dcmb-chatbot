# Volunteer Check-In Kiosk

A standalone iPad check-in app. Volunteers tap their name, pick what they're checking in for, and see a welcome screen. Then the kiosk goes back to its home screen, its name list, or the app that launched it. Each check-in is logged, and you can download the log as a spreadsheet (CSV).

This folder is self-contained. It shares no code or Azure resources with anything else, so you can move it into its own repository as-is (see [Moving to its own repo](#moving-to-its-own-repo)).

```
Kiosk (index.html) ─┐
Admin (admin.html) ─┴─► Azure Functions API ─► Azure Table Storage
   hosted on the same storage account's static website
```

**Cost:** a few cents a month. The consumption-plan Functions, Table Storage and static website all stay inside free or near-free usage at kiosk volumes.

---

## What gets saved

Each check-in is saved as one row in the `volunteercheckins` table. The admin page exports these rows as CSV:

| Column | Example |
|---|---|
| `date` | 2026-10-28 (local, `KIOSK_TIMEZONE`, default `America/Chicago`) |
| `time` | 18:42:07 (local) |
| `name` | Jane Smith |
| `activity` | Concessions (or `General` if no activities are defined) |
| `walk_in` | `yes` if the person typed their name instead of picking it |
| `checked_in_at_utc` | 2026-10-28T23:42:07+00:00 |

---

## Launching from another application

The kiosk is a plain URL, so any app, web page, MDM profile or iOS Shortcut can open it. Set its behavior with query parameters:

| Parameter | Effect |
|---|---|
| `start=names` | Skip the kiosk home screen and open straight on the name list |
| `return=<url>` | Go back to this URL (e.g. your app's kiosk home) after the welcome screen, when Back is tapped, or after 45 s idle |
| `activity=<name>` | Lock to one activity, so the "what are you checking in for?" question is skipped |
| `key=<KIOSK_API_KEY>` | Needed only if you set a kiosk key |

Example: your app links to

```
https://<storage>.z13.web.core.windows.net/?start=names&activity=Concessions&return=https%3A%2F%2Fyour-app.example.com%2Fkiosk
```

The admin page's **Kiosk Link** section builds this URL for you.

- Check-ins that can't be sent right away (Wi-Fi drop) are queued on the device and synced later with their original tap time. Before following `return`, the kiosk waits up to 2 s for the queue to send.
- If your app hosts its own copy of `index.html` on a different domain, add that origin to `extra_cors_origins` in `terraform.tfvars`.
- The page can also be embedded in an `<iframe>`.

### Standalone iPad (no other app)

1. Open the kiosk URL in Safari → Share → **Add to Home Screen**. It then launches full-screen.
2. Settings → Accessibility → **Guided Access** on. Triple-click the side or home button in the kiosk to lock the iPad to it.
3. Settings → Display & Brightness → Auto-Lock → **Never**, and keep the iPad plugged in.

---

## Admin page (`admin.html`)

Sign in with `ADMIN_API_KEY`. From there you can:

- **Volunteer names:** paste one name per line (e.g. a column copied from Excel). Duplicates are skipped.
- **Activities:** e.g. Concessions, Pit Crew, Chaperone. With none defined, check-ins are recorded as `General`. With one, the kiosk skips the question.
- **Check-in log:** pick a date range, view it, and use **Download spreadsheet (CSV)**. Walk-ins can be added to the name list in one click.
- **Kiosk link builder:** see above.

---

## API

All routes are under `/api`. Kiosk routes require `X-Kiosk-Key` only when `KIOSK_API_KEY` is set. Admin routes always require `X-Admin-Key`.

| Route | Who | Purpose |
|---|---|---|
| `GET /kiosk` | kiosk | Names + activities |
| `POST /checkin` | kiosk | `{volunteer_id \| name, activity_id \| activity, checked_in_at?}` |
| `GET/POST/DELETE /roster` | admin | List / add (`{names:[…]}`) / remove (`?id=`) names |
| `GET/POST/DELETE /activities` | admin | List / add (`{name}`) / remove (`?id=`) |
| `GET/DELETE /checkins` | admin | `?from=YYYY-MM-DD&to=YYYY-MM-DD[&format=csv]`; delete with `?id=` |

Other systems can use the same API to pull check-ins (e.g. `Invoke-RestMethod` with `X-Admin-Key`).

---

## Setup (Azure)

Requires the Azure CLI and Terraform ≥ 1.9.

```powershell
az login
.\scripts\bootstrap-tfstate.ps1            # once: Terraform state storage + infra\backend.hcl

Copy-Item infra\terraform.tfvars.example infra\terraform.tfvars
notepad infra\terraform.tfvars              # subscription_id, admin_api_key, …

.\scripts\deploy.ps1                        # infra + API + web pages; prints the kiosk/admin URLs
```

Re-run `.\scripts\deploy.ps1 -SkipInfra` to push code changes only.

### Deploying with GitHub Actions (optional)

`.github/workflows/deploy.yml` deploys on push to `main`. It needs these secrets:

| Secret | Value |
|---|---|
| `AZURE_CREDENTIALS` | `az ad sp create-for-rbac --name vol-checkin-deploy --role contributor --scopes /subscriptions/<id> --sdk-auth` |
| `TFSTATE_RESOURCE_GROUP` / `TFSTATE_STORAGE_ACCOUNT` | Printed by `bootstrap-tfstate.ps1` |
| `ADMIN_API_KEY` | Admin page key |
| `KIOSK_API_KEY` | Optional kiosk key |

The service principal also needs **Storage Blob Data Contributor** on the state storage account.

Edit `ORG_NAME` in `frontend/js/config.js` to change the name shown on the kiosk.

---

## Local development

```powershell
# Start Azurite (VS Code "Azurite: Start", or `azurite` from npm), then:
cd backend
pip install -r requirements-dev.txt
Copy-Item local.settings.json.example local.settings.json
func start
```

Open `frontend/index.html` and `frontend/admin.html` with VS Code Live Server. `config.js` already points to `http://localhost:7071/api`.

Tests:

```powershell
cd backend; python -m pytest tests -v; ruff check .
cd ..\frontend-tests; npm install; npx vitest run
```

---

## Moving to its own repo

```powershell
# From the repo this folder currently lives in:
git subtree split --prefix volunteer-checkin -b volunteer-checkin-only
git push https://github.com/<you>/volunteer-checkin.git volunteer-checkin-only:main
```

The `.github/workflows` here only run once this folder is the root of its own repository.
