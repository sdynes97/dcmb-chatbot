// ── Auth ─────────────────────────────────────────────────────────────────────

let apiKey = "";

function authHeaders() {
  return { "Content-Type": "application/json", "X-Admin-Key": apiKey };
}

// Escape untrusted strings before inserting into innerHTML (defense-in-depth
// against stored XSS — event data is admin-written but never trust it blindly).
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function saveKey(key) {
  if (document.getElementById("remember-me").checked) {
    localStorage.setItem("dcmb_admin_key", key);
  }
}

function loadSavedKey() {
  return localStorage.getItem("dcmb_admin_key") || "";
}

function signIn(key) {
  apiKey = key;
  document.getElementById("auth-card").style.display = "none";
  document.getElementById("admin-content").style.display = "block";
  loadETA();
  loadEvents();
}

// Auto sign-in if a saved key exists
const saved = loadSavedKey();
if (saved) {
  fetch(`${API_BASE_URL}/admin/events`, {
    headers: { "X-Admin-Key": saved },
  }).then((r) => {
    if (r.ok) signIn(saved);
  });
}

document.getElementById("auth-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const key = document.getElementById("api-key").value.trim();
  if (!key) return;
  const r = await fetch(`${API_BASE_URL}/admin/events`, {
    headers: { "X-Admin-Key": key },
  });
  if (r.status === 401) { toast("Invalid access key.", true); return; }
  saveKey(key);
  signIn(key);
});

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("dcmb_admin_key");
  apiKey = "";
  document.getElementById("admin-content").style.display = "none";
  document.getElementById("auth-card").style.display = "block";
  document.getElementById("api-key").value = "";
});

// ── Toast ─────────────────────────────────────────────────────────────────────

let _toastTimer;
function toast(msg, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = "show" + (isError ? " error" : "");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => { el.className = ""; }, 3500);
}

// ── ETA ───────────────────────────────────────────────────────────────────────

async function loadETA() {
  const r = await fetch(`${API_BASE_URL}/location`);
  const data = await r.json();
  const el = document.getElementById("eta-current");
  if (data.eta) {
    const t = new Date(data.eta.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    el.textContent = `Current: "${data.eta.message}" — posted at ${t}`;
    el.className = "eta-current";
  } else {
    el.textContent = "No ETA update set";
    el.className = "eta-current none";
  }
}

document.getElementById("eta-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const btn = e.target.querySelector("button[type=submit]");
  btn.disabled = true;
  try {
    const r = await fetch(`${API_BASE_URL}/location`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ message: fd.get("eta_message"), eta_time: fd.get("eta_time") || "" }),
    });
    if (!r.ok) { toast("Failed to post ETA.", true); return; }
    toast("ETA update posted ✓");
    e.target.reset();
    loadETA();
  } catch { toast("Network error.", true); }
  finally { btn.disabled = false; }
});

document.getElementById("clear-eta-btn").addEventListener("click", async () => {
  if (!confirm("Clear the current ETA update?")) return;
  await fetch(`${API_BASE_URL}/location`, { method: "DELETE", headers: authHeaders() });
  toast("ETA cleared.");
  loadETA();
});

// ── Events ────────────────────────────────────────────────────────────────────

let _allEvents = [];

async function loadEvents() {
  const r = await fetch(`${API_BASE_URL}/admin/events`, { headers: authHeaders() });
  _allEvents = await r.json();
  renderDesktopTable(_allEvents);
  renderMobileCards(_allEvents);
}

// ── Desktop table ─────────────────────────────────────────────────────────────

function renderDesktopTable(events) {
  const tbody = document.getElementById("events-tbody");
  if (!events.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="color:#aaa">No events yet.</td></tr>';
    return;
  }
  tbody.innerHTML = events.map((ev) => `
    <tr>
      <td>${esc(ev.event_date)}</td>
      <td>${esc(ev.event_name)}</td>
      <td>${esc(ev.event_type.replace("_", " "))}</td>
      <td>${esc(ev.call_time)}</td>
      <td>${esc(ev.performance_time)}</td>
      <td>${esc(ev.estimated_return)}</td>
      <td>${ev.is_away ? "✈ Away" : "Home"}</td>
      <td>
        <button class="btn btn-outline btn-sm" data-action="edit" data-rk="${esc(ev.row_key)}">Edit</button>
        <button class="btn btn-danger btn-sm" data-action="delete" data-rk="${esc(ev.row_key)}">Delete</button>
      </td>
    </tr>
  `).join("");
}

// Delegated listener — looks events up by row_key from _allEvents, so no
// untrusted data is interpolated into inline handlers.
document.getElementById("events-tbody").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const ev = _allEvents.find((x) => x.row_key === btn.dataset.rk);
  if (!ev) return;
  if (btn.dataset.action === "edit") editEvent(ev);
  else if (btn.dataset.action === "delete") deleteEvent(ev.partition_key, ev.row_key);
});

// ── Mobile event cards ────────────────────────────────────────────────────────

function renderMobileCards(events) {
  const container = document.getElementById("mobile-events-list");
  const upcoming = events.filter((e) => e.event_date >= today());
  if (!upcoming.length) {
    container.innerHTML = '<p style="color:#aaa;font-size:0.9rem">No upcoming events.</p>';
    return;
  }
  container.innerHTML = upcoming.map((ev) => `
    <div class="event-card" id="mobile-card-${esc(ev.row_key)}">
      <div class="event-card-header">
        <div>
          <div class="event-card-title">${esc(ev.event_name)}</div>
          <div class="event-card-date">${esc(formatDate(ev.event_date))}</div>
        </div>
        <span class="event-card-badge ${ev.is_away ? "away" : ""}">
          ${ev.is_away ? "✈ Away" : "Home"}
        </span>
      </div>
      <div class="times-row">
        <div>
          <label>Call Time</label>
          <input type="time" id="m-call-${esc(ev.row_key)}" value="${esc(ev.call_time)}" />
        </div>
        <div>
          <label>Performance</label>
          <input type="time" id="m-perf-${esc(ev.row_key)}" value="${esc(ev.performance_time)}" />
        </div>
        <div>
          <label>Est. Return</label>
          <input type="time" id="m-return-${esc(ev.row_key)}" value="${esc(ev.estimated_return)}" />
        </div>
      </div>
      <div>
        <label>Notes</label>
        <input type="text" id="m-notes-${esc(ev.row_key)}" value="${esc(ev.notes || "")}"
          placeholder="Optional note for parents…" style="margin-bottom:0" />
      </div>
      <div class="event-card-actions">
        <button class="btn btn-primary btn-sm" data-action="save-mobile" data-rk="${esc(ev.row_key)}">
          Save Changes
        </button>
      </div>
    </div>
  `).join("");
}

document.getElementById("mobile-events-list").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-action='save-mobile']");
  if (btn) saveMobileCard(btn.dataset.rk);
});

async function saveMobileCard(rk) {
  const ev = _allEvents.find((x) => x.row_key === rk);
  if (!ev) return;
  const updated = {
    ...ev,
    call_time:         document.getElementById(`m-call-${rk}`).value,
    performance_time:  document.getElementById(`m-perf-${rk}`).value,
    estimated_return:  document.getElementById(`m-return-${rk}`).value,
    notes:             document.getElementById(`m-notes-${rk}`).value,
  };
  const btn = document.querySelector(`#mobile-card-${rk} .btn-primary`);
  btn.disabled = true;
  btn.textContent = "Saving…";
  try {
    const r = await fetch(`${API_BASE_URL}/admin/events`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(updated),
    });
    if (!r.ok) { toast("Failed to save.", true); return; }
    toast(`${ev.event_name} updated ✓`);
    // Update local cache
    const idx = _allEvents.findIndex((e) => e.row_key === rk);
    if (idx > -1) _allEvents[idx] = updated;
    renderDesktopTable(_allEvents);
  } catch { toast("Network error.", true); }
  finally { btn.disabled = false; btn.textContent = "Save Changes"; }
}

// ── Desktop add / edit form ───────────────────────────────────────────────────

function editEvent(ev) {
  const fields = [
    "event_name", "event_type", "event_date", "call_time",
    "performance_time", "estimated_return", "location_name",
    "location_address", "drop_off_location", "notes",
    "partition_key", "row_key",
  ];
  fields.forEach((f) => {
    const el = document.getElementById(f);
    if (el) el.value = ev[f] ?? "";
  });
  document.getElementById("is_away").checked = !!ev.is_away;
  document.getElementById("event-form-title").textContent = "✏️ Edit Event";
  document.getElementById("cancel-edit-btn").style.display = "inline-flex";
  document.getElementById("event-form-card").scrollIntoView({ behavior: "smooth" });
}

function cancelEdit() {
  document.getElementById("event-form").reset();
  document.getElementById("partition_key").value = "";
  document.getElementById("row_key").value = "";
  document.getElementById("event-form-title").textContent = "➕ Add Event";
  document.getElementById("cancel-edit-btn").style.display = "none";
}

document.getElementById("event-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd.entries());
  body.is_away = document.getElementById("is_away").checked;

  // Auto-generate row_key and partition_key if adding new
  if (!body.row_key) {
    const slug = body.event_name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
    body.row_key = `${body.event_date}_${slug}`;
  }
  if (!body.partition_key) {
    body.partition_key = body.event_date.substring(0, 4);
  }

  const btn = document.getElementById("save-event-btn");
  btn.disabled = true;
  try {
    const r = await fetch(`${API_BASE_URL}/admin/events`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(body),
    });
    if (!r.ok) { toast("Failed to save event.", true); return; }
    toast("Event saved ✓");
    cancelEdit();
    loadEvents();
  } catch { toast("Network error.", true); }
  finally { btn.disabled = false; }
});

async function deleteEvent(partitionKey, rowKey) {
  if (!confirm("Delete this event? This cannot be undone.")) return;
  const r = await fetch(
    `${API_BASE_URL}/admin/events?partition_key=${encodeURIComponent(partitionKey)}&row_key=${encodeURIComponent(rowKey)}`,
    { method: "DELETE", headers: authHeaders() }
  );
  if (!r.ok) { toast("Failed to delete.", true); return; }
  toast("Event deleted.");
  loadEvents();
}

// ── Live GPS Tracking ─────────────────────────────────────────────────────────

let _trackingInterval = null;
let _watchId = null;
let _lastSent = null;

const trackingStatus  = document.getElementById("tracking-status");
const startTrackingBtn = document.getElementById("start-tracking-btn");
const stopTrackingBtn  = document.getElementById("stop-tracking-btn");

startTrackingBtn.addEventListener("click", startTracking);
stopTrackingBtn.addEventListener("click", stopTracking);

function startTracking() {
  if (!("geolocation" in navigator)) {
    setTrackingStatus("error", "❌ This browser does not support location sharing.");
    return;
  }

  setTrackingStatus("active", "📍 Requesting location permission…");

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      sendLocation(pos);
      // Send an update every 30 seconds
      _trackingInterval = setInterval(() => {
        navigator.geolocation.getCurrentPosition(sendLocation, onGeoError, {
          enableHighAccuracy: true,
          timeout: 10000,
        });
      }, 30000);

      startTrackingBtn.style.display = "none";
      stopTrackingBtn.style.display  = "inline-flex";
    },
    onGeoError,
    { enableHighAccuracy: true, timeout: 15000 },
  );
}

function stopTracking() {
  clearInterval(_trackingInterval);
  _trackingInterval = null;
  if (_watchId !== null) {
    navigator.geolocation.clearWatch(_watchId);
    _watchId = null;
  }
  setTrackingStatus("idle", "📍 Live tracking stopped.");
  startTrackingBtn.style.display = "inline-flex";
  stopTrackingBtn.style.display  = "none";
}

async function sendLocation(pos) {
  const { latitude: lat, longitude: lng } = pos.coords;
  try {
    const r = await fetch(`${API_BASE_URL}/location/track`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ lat, lng }),
    });
    if (!r.ok) { setTrackingStatus("error", "❌ Failed to send location. Check your key."); return; }
    const data = await r.json();
    _lastSent = new Date();
    const timeStr = _lastSent.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setTrackingStatus("active",
      `📍 Tracking active — ${data.eta.distance_mi} mi from school, ` +
      `ETA ~${fmtTime(data.eta.eta_iso)} (updated ${timeStr})`
    );
    loadETA();
  } catch {
    setTrackingStatus("error", "❌ Network error — will retry in 30s.");
  }
}

function onGeoError(err) {
  const msgs = {
    1: "Location permission denied. Please allow location access and try again.",
    2: "Location unavailable. Are you indoors?",
    3: "Location request timed out. Will retry.",
  };
  setTrackingStatus("error", "❌ " + (msgs[err.code] || "Location error."));
}

function setTrackingStatus(state, text) {
  trackingStatus.textContent = text;
  trackingStatus.className = `tracking-${state}`;
}

function fmtTime(isoStr) {
  return new Date(isoStr).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// Stop tracking automatically if the page is hidden (phone screen off / tab switched)
document.addEventListener("visibilitychange", () => {
  if (document.hidden && _trackingInterval) {
    setTrackingStatus("active",
      "⏸ Screen locked — tracking paused. Return to this page to resume."
    );
    clearInterval(_trackingInterval);
    _trackingInterval = null;
  } else if (!document.hidden && stopTrackingBtn.style.display !== "none") {
    // Page is visible again and tracking was active — resume
    setTrackingStatus("active", "📍 Tracking resumed…");
    startTracking();
    startTrackingBtn.style.display = "none";
    stopTrackingBtn.style.display  = "inline-flex";
  }
});

// ── Helpers ───────────────────────────────────────────────────────────────────

function today() {
  return new Date().toISOString().slice(0, 10);
}

function formatDate(iso) {
  const [y, m, d] = iso.split("-");
  return new Date(y, m - 1, d).toLocaleDateString([], {
    weekday: "short", month: "short", day: "numeric",
  });
}
