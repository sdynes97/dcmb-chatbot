// ── Volunteer admin: roster, activities, check-in log & CSV export ──────────

let apiKey = "";
let roster = [];
let activities = [];

function authHeaders() {
  return { "Content-Type": "application/json", "X-Admin-Key": apiKey };
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function toast(msg, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = `show${isError ? " error" : ""}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.className = ""), 3000);
}

function localDate(d = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

async function api(path, options = {}) {
  const r = await fetch(`${API_BASE_URL}${path}`, { ...options, headers: authHeaders() });
  if (r.status === 401) {
    signOut();
    throw new Error("Session expired — sign in again");
  }
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    throw new Error(data.error || `Request failed (${r.status})`);
  }
  return r;
}

// ── Auth ─────────────────────────────────────────────────────────────────────

async function trySignIn(key) {
  const r = await fetch(`${API_BASE_URL}/activities`, { headers: { "X-Admin-Key": key } });
  if (!r.ok) return false;
  apiKey = key;
  localStorage.setItem("vc_admin_key", key);
  document.getElementById("auth-card").style.display = "none";
  document.getElementById("vol-content").style.display = "block";
  activities = await r.json();
  renderActivities();
  loadRoster();
  loadLog();
  return true;
}

function signOut() {
  apiKey = "";
  localStorage.removeItem("vc_admin_key");
  document.getElementById("auth-card").style.display = "block";
  document.getElementById("vol-content").style.display = "none";
}

document.getElementById("auth-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const key = document.getElementById("api-key").value.trim();
  if (!(await trySignIn(key))) toast("Invalid access key", true);
});

document.getElementById("logout-btn").addEventListener("click", signOut);

// ── Activities ───────────────────────────────────────────────────────────────

async function loadActivities() {
  activities = await (await api("/activities")).json();
  renderActivities();
}

function renderActivities() {
  const list = document.getElementById("activity-list");
  list.innerHTML = activities.length
    ? activities.map((a) => `
        <span class="chip">${esc(a.name)}
          <button type="button" title="Remove" data-action="del-activity" data-id="${esc(a.id)}">×</button>
        </span>`).join("")
    : `<span class="hint">No activities yet — check-ins will be recorded as “General”.</span>`;

  const select = document.getElementById("kiosk-activity");
  const current = select.value;
  select.innerHTML = `<option value="">Ask each volunteer</option>` +
    activities.map((a) => `<option value="${esc(a.name)}">${esc(a.name)}</option>`).join("");
  select.value = activities.some((a) => a.name === current) ? current : "";
  renderKioskLink();
}

document.getElementById("activity-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("activity-name");
  try {
    await api("/activities", { method: "POST", body: JSON.stringify({ name: input.value }) });
    input.value = "";
    await loadActivities();
    toast("Activity added");
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("activity-list").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-action='del-activity']");
  if (!btn) return;
  const a = activities.find((x) => x.id === btn.dataset.id);
  if (!a || !confirm(`Remove "${a.name}"? Past check-ins keep their activity name.`)) return;
  try {
    await api(`/activities?id=${encodeURIComponent(a.id)}`, { method: "DELETE" });
    await loadActivities();
  } catch (err) {
    toast(err.message, true);
  }
});

// ── Roster ───────────────────────────────────────────────────────────────────

async function loadRoster() {
  try {
    roster = await (await api("/roster")).json();
    renderRoster();
    renderLog(); // walk-in "Add to list" buttons depend on the roster
  } catch (err) {
    toast(err.message, true);
  }
}

function renderRoster() {
  const q = document.getElementById("roster-search").value.trim().toLowerCase();
  const list = roster.filter((v) => !q || v.name.toLowerCase().includes(q));
  document.getElementById("roster-count").textContent =
    `${roster.length} volunteer${roster.length === 1 ? "" : "s"}${q ? ` · ${list.length} shown` : ""}`;
  document.getElementById("roster-tbody").innerHTML = list.map((v) => `
    <tr>
      <td>${esc(v.name)}</td>
      <td style="text-align:right">
        <button class="btn btn-outline btn-sm" data-action="del-volunteer" data-id="${esc(v.id)}">Remove</button>
      </td>
    </tr>`).join("");
}

async function addNames(names) {
  const r = await api("/roster", { method: "POST", body: JSON.stringify({ names }) });
  const data = await r.json();
  await loadRoster();
  return data.added.length;
}

document.getElementById("roster-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const textarea = document.getElementById("roster-names");
  const names = textarea.value.split(/\r?\n/).map((n) => n.trim()).filter(Boolean);
  if (!names.length) return;
  try {
    const added = await addNames(names);
    textarea.value = "";
    toast(`Added ${added} name${added === 1 ? "" : "s"}${added < names.length ? " (duplicates skipped)" : ""}`);
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("roster-search").addEventListener("input", renderRoster);

document.getElementById("roster-tbody").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-action='del-volunteer']");
  if (!btn) return;
  const v = roster.find((x) => x.id === btn.dataset.id);
  if (!v || !confirm(`Remove ${v.name} from the kiosk list? Past check-ins are kept.`)) return;
  try {
    await api(`/roster?id=${encodeURIComponent(v.id)}`, { method: "DELETE" });
    await loadRoster();
  } catch (err) {
    toast(err.message, true);
  }
});

// ── Check-in log ─────────────────────────────────────────────────────────────

let logRows = [];

function logRange() {
  const from = document.getElementById("log-from").value || localDate();
  const to = document.getElementById("log-to").value || from;
  return `from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`;
}

async function loadLog() {
  try {
    logRows = await (await api(`/checkins?${logRange()}`)).json();
    renderLog();
  } catch (err) {
    toast(err.message, true);
  }
}

function formatTime(hms) {
  const [h, m] = hms.split(":").map(Number);
  if (Number.isNaN(h)) return hms;
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${h < 12 ? "AM" : "PM"}`;
}

function renderLog() {
  const onRoster = new Set(roster.map((v) => v.name.toLowerCase()));
  document.getElementById("log-count").textContent =
    `${logRows.length} check-in${logRows.length === 1 ? "" : "s"}`;
  document.getElementById("log-tbody").innerHTML = logRows.length
    ? logRows.map((c) => `
      <tr>
        <td>${esc(c.date)}</td>
        <td>${esc(formatTime(c.time))}</td>
        <td>${esc(c.name)} ${c.walk_in ? `<span class="tag">walk-in</span>` : ""}</td>
        <td>${esc(c.activity)}</td>
        <td style="text-align:right;white-space:nowrap">
          ${c.walk_in && !onRoster.has(c.name.toLowerCase())
            ? `<button class="btn btn-outline btn-sm" data-action="add-walkin" data-name="${esc(c.name)}">Add to list</button>`
            : ""}
          <button class="btn btn-outline btn-sm" data-action="del-checkin" data-id="${esc(c.id)}">Delete</button>
        </td>
      </tr>`).join("")
    : `<tr><td colspan="5" style="color:#aaa">No check-ins for these dates.</td></tr>`;
}

document.getElementById("log-load-btn").addEventListener("click", loadLog);

document.getElementById("log-tbody").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  try {
    if (btn.dataset.action === "add-walkin") {
      await addNames([btn.dataset.name]);
      renderLog();
      toast(`${btn.dataset.name} added to the kiosk list`);
    } else if (btn.dataset.action === "del-checkin") {
      if (!confirm("Delete this check-in?")) return;
      await api(`/checkins?id=${encodeURIComponent(btn.dataset.id)}`, { method: "DELETE" });
      await loadLog();
    }
  } catch (err) {
    toast(err.message, true);
  }
});

document.getElementById("log-csv-btn").addEventListener("click", async () => {
  try {
    const r = await api(`/checkins?${logRange()}&format=csv`);
    const blob = await r.blob();
    const match = /filename="([^"]+)"/.exec(r.headers.get("Content-Disposition") || "");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = match ? match[1] : "volunteer-checkins.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  } catch (err) {
    toast(err.message, true);
  }
});

// ── Kiosk link ───────────────────────────────────────────────────────────────

function kioskUrl() {
  const url = new URL("index.html", location.href);
  const key = document.getElementById("kiosk-key").value.trim();
  const activity = document.getElementById("kiosk-activity").value;
  const returnUrl = document.getElementById("kiosk-return").value.trim();
  const start = document.getElementById("kiosk-start").value;
  if (key) url.searchParams.set("key", key);
  if (activity) url.searchParams.set("activity", activity);
  if (returnUrl) url.searchParams.set("return", returnUrl);
  if (start) url.searchParams.set("start", start);
  return url.toString();
}

function renderKioskLink() {
  const url = kioskUrl();
  document.getElementById("kiosk-link").textContent = url;
  document.getElementById("kiosk-open-btn").href = url;
}

document.getElementById("kiosk-key").addEventListener("input", renderKioskLink);
document.getElementById("kiosk-activity").addEventListener("change", renderKioskLink);
document.getElementById("kiosk-return").addEventListener("input", renderKioskLink);
document.getElementById("kiosk-start").addEventListener("change", renderKioskLink);
document.getElementById("kiosk-copy-btn").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(kioskUrl());
    toast("Link copied");
  } catch {
    toast("Couldn't copy — select the link and copy it manually", true);
  }
});

// ── Start ────────────────────────────────────────────────────────────────────

if (typeof ORG_NAME !== "undefined" && ORG_NAME) {
  document.getElementById("org-title").textContent = `${ORG_NAME} — Volunteer Check-In`;
}
document.getElementById("log-from").value = localDate();
document.getElementById("log-to").value = localDate();
renderKioskLink();

const saved = localStorage.getItem("vc_admin_key");
if (saved) trySignIn(saved).catch(() => {});
