const API_KEY_INPUT = document.getElementById("api-key");
const AUTH_SECTION = document.getElementById("auth-section");
const ADMIN_SECTION = document.getElementById("admin-section");
const EVENTS_TABLE = document.getElementById("events-tbody");
const EVENT_FORM = document.getElementById("event-form");
const ETA_FORM = document.getElementById("eta-form");
const ETA_STATUS = document.getElementById("eta-status");
const MSG = document.getElementById("message");

let apiKey = "";

function showMsg(text, isError = false) {
  MSG.textContent = text;
  MSG.className = isError ? "msg error" : "msg success";
  setTimeout(() => { MSG.textContent = ""; MSG.className = "msg"; }, 4000);
}

function authHeaders() {
  return { "Content-Type": "application/json", "X-Admin-Key": apiKey };
}

document.getElementById("auth-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  apiKey = API_KEY_INPUT.value.trim();
  if (!apiKey) return;

  // Test the key by fetching events
  try {
    const resp = await fetch(`${API_BASE_URL}/admin/events`, { headers: authHeaders() });
    if (resp.status === 401) { showMsg("Invalid API key.", true); return; }
    const events = await resp.json();
    AUTH_SECTION.style.display = "none";
    ADMIN_SECTION.style.display = "block";
    renderEvents(events);
    loadETA();
  } catch {
    showMsg("Connection error.", true);
  }
});

function renderEvents(events) {
  EVENTS_TABLE.innerHTML = "";
  events.forEach((ev) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${ev.event_date}</td>
      <td>${ev.event_name}</td>
      <td>${ev.event_type}</td>
      <td>${ev.call_time}</td>
      <td>${ev.performance_time}</td>
      <td>${ev.estimated_return}</td>
      <td>${ev.is_away ? "Away" : "Home"}</td>
      <td>
        <button class="btn-sm" onclick="editEvent(${JSON.stringify(ev).replace(/"/g, "&quot;")})">Edit</button>
        <button class="btn-sm danger" onclick="deleteEvent('${ev.partition_key}','${ev.row_key}')">Delete</button>
      </td>
    `;
    EVENTS_TABLE.appendChild(tr);
  });
}

async function loadETA() {
  try {
    const resp = await fetch(`${API_BASE_URL}/location`);
    const data = await resp.json();
    if (data.eta) {
      ETA_STATUS.textContent = `Current: "${data.eta.message}" (updated ${data.eta.updated_at})`;
    } else {
      ETA_STATUS.textContent = "No ETA currently set.";
    }
  } catch {
    ETA_STATUS.textContent = "Could not load ETA.";
  }
}

ETA_FORM.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(ETA_FORM);
  const body = { message: fd.get("eta_message"), eta_time: fd.get("eta_time") || "" };
  try {
    const resp = await fetch(`${API_BASE_URL}/location`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(body),
    });
    if (!resp.ok) { showMsg("Failed to update ETA.", true); return; }
    showMsg("ETA updated successfully.");
    ETA_FORM.reset();
    loadETA();
  } catch {
    showMsg("Connection error.", true);
  }
});

document.getElementById("clear-eta-btn").addEventListener("click", async () => {
  if (!confirm("Clear the current ETA update?")) return;
  try {
    await fetch(`${API_BASE_URL}/location`, { method: "DELETE", headers: authHeaders() });
    showMsg("ETA cleared.");
    loadETA();
  } catch {
    showMsg("Connection error.", true);
  }
});

EVENT_FORM.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(EVENT_FORM);
  const body = Object.fromEntries(fd.entries());
  body.is_away = body.is_away === "on";

  // Auto-generate row_key if empty
  if (!body.row_key) {
    const slug = body.event_name.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
    body.row_key = `${body.event_date}_${slug}`;
  }
  if (!body.partition_key) {
    body.partition_key = body.event_date.substring(0, 4);
  }

  try {
    const resp = await fetch(`${API_BASE_URL}/admin/events`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(body),
    });
    if (!resp.ok) { showMsg("Failed to save event.", true); return; }
    showMsg("Event saved.");
    EVENT_FORM.reset();
    document.getElementById("row_key").value = "";
    refreshEvents();
  } catch {
    showMsg("Connection error.", true);
  }
});

function editEvent(ev) {
  document.getElementById("event_name").value = ev.event_name;
  document.getElementById("event_type").value = ev.event_type;
  document.getElementById("event_date").value = ev.event_date;
  document.getElementById("call_time").value = ev.call_time;
  document.getElementById("performance_time").value = ev.performance_time;
  document.getElementById("estimated_return").value = ev.estimated_return;
  document.getElementById("location_name").value = ev.location_name;
  document.getElementById("location_address").value = ev.location_address;
  document.getElementById("drop_off_location").value = ev.drop_off_location;
  document.getElementById("notes").value = ev.notes || "";
  document.getElementById("is_away").checked = ev.is_away;
  document.getElementById("partition_key").value = ev.partition_key;
  document.getElementById("row_key").value = ev.row_key;
  document.getElementById("event_name").scrollIntoView({ behavior: "smooth" });
}

async function deleteEvent(partitionKey, rowKey) {
  if (!confirm("Delete this event?")) return;
  try {
    const resp = await fetch(
      `${API_BASE_URL}/admin/events?partition_key=${encodeURIComponent(partitionKey)}&row_key=${encodeURIComponent(rowKey)}`,
      { method: "DELETE", headers: authHeaders() }
    );
    if (!resp.ok) { showMsg("Failed to delete event.", true); return; }
    showMsg("Event deleted.");
    refreshEvents();
  } catch {
    showMsg("Connection error.", true);
  }
}

async function refreshEvents() {
  const resp = await fetch(`${API_BASE_URL}/admin/events`, { headers: authHeaders() });
  const events = await resp.json();
  renderEvents(events);
}
