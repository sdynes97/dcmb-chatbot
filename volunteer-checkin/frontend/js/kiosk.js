// ── Volunteer check-in kiosk (iPad) ──────────────────────────────────────────
//
// URL options — another app can launch the kiosk with any of these:
//   ?key=<KIOSK_API_KEY>       required if the backend has a kiosk key set
//   ?activity=<activity name>  lock the kiosk to one activity (skips the picker)
//   ?start=names               open straight on the name list (skip home screen)
//   ?return=<url>              go back to this URL (e.g. the launching app)
//                              after check-in, on Back, or when left idle
//
// Check-ins are queued in localStorage and retried, so a Wi-Fi blip never
// loses a tap; the original tap time is sent along with each queued check-in.

const WELCOME_MS = 5000;
const IDLE_MS = 45000;
const REFRESH_MS = 5 * 60 * 1000;
const FLUSH_MS = 30000;

const LS_KEY = "vc_kiosk_key";
const LS_DATA = "vc_kiosk_data";
const LS_QUEUE = "vc_kiosk_queue";

const params = new URLSearchParams(location.search);
if (params.get("key")) localStorage.setItem(LS_KEY, params.get("key"));
const kioskKey = localStorage.getItem(LS_KEY) || "";
const lockedActivity = (params.get("activity") || "").trim();
const startOnNames = params.get("start") === "names";
const returnUrl = safeReturnUrl(params.get("return"));

function safeReturnUrl(raw) {
  // Only http(s) — never javascript: or other schemes.
  if (!raw) return "";
  try {
    const u = new URL(raw, location.href);
    return u.protocol === "http:" || u.protocol === "https:" ? u.toString() : "";
  } catch {
    return "";
  }
}

let volunteers = [];
let activities = [];
let pendingVolunteer = null; // { id, name } — id is "" for walk-ins
let activeLetter = "";
let idleTimer = null;
let welcomeTimer = null;

function headers() {
  const h = { "Content-Type": "application/json" };
  if (kioskKey) h["X-Kiosk-Key"] = kioskKey;
  return h;
}

function readJSON(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) ?? fallback;
  } catch {
    return fallback;
  }
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// ── Screens ──────────────────────────────────────────────────────────────────

function show(name) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  document.getElementById(`screen-${name}`).classList.add("active");
  clearTimeout(idleTimer);
  clearTimeout(welcomeTimer);
  if (name !== "home" && name !== "error") resetIdle();
  if (name === "home") {
    pendingVolunteer = null;
    document.activeElement?.blur();
  }
}

function resetIdle() {
  clearTimeout(idleTimer);
  idleTimer = setTimeout(goHome, IDLE_MS);
}

function goHome() {
  if (returnUrl) {
    // Give queued check-ins a moment to send, but never strand the kiosk.
    const timeout = new Promise((resolve) => setTimeout(resolve, 2000));
    Promise.race([flushQueue(), timeout]).finally(() => location.assign(returnUrl));
    return;
  }
  // When launched straight onto the name list, that list *is* home.
  if (startOnNames) {
    goNames();
    return;
  }
  show("home");
}

function goNames() {
  const search = document.getElementById("name-search");
  search.value = "";
  activeLetter = "";
  renderNames();
  show("names");
}

// ── Data ─────────────────────────────────────────────────────────────────────

function applyData(data) {
  volunteers = data.volunteers || [];
  activities = data.activities || [];
  renderLetters();
  renderNames();
  renderHomeActivity();
}

async function loadData() {
  try {
    const r = await fetch(`${API_BASE_URL}/kiosk`, { headers: headers() });
    if (r.status === 401) {
      showError("This iPad isn't authorized. Open the kiosk link that includes ?key=… from the admin page.");
      return;
    }
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    localStorage.setItem(LS_DATA, JSON.stringify(data));
    applyData(data);
    if (document.getElementById("screen-error").classList.contains("active")) show("home");
  } catch {
    // Offline — fall back to the last list we saw.
    const cached = readJSON(LS_DATA, null);
    if (cached) {
      applyData(cached);
    } else {
      showError("Can't reach the check-in server. Check the iPad's Wi-Fi.");
    }
  }
}

function showError(message) {
  document.getElementById("error-detail").textContent = message;
  show("error");
}

// ── Rendering ────────────────────────────────────────────────────────────────

function matchesLetter(name, letter) {
  return name.split(/\s+/).some((w) => w.toUpperCase().startsWith(letter));
}

function filteredVolunteers() {
  const q = document.getElementById("name-search").value.trim().toLowerCase();
  return volunteers.filter((v) => {
    if (activeLetter && !matchesLetter(v.name, activeLetter)) return false;
    return !q || v.name.toLowerCase().includes(q);
  });
}

function renderLetters() {
  const bar = document.getElementById("letter-bar");
  bar.replaceChildren();
  for (const letter of "ABCDEFGHIJKLMNOPQRSTUVWXYZ") {
    const btn = el("button", letter === activeLetter ? "active" : "", letter);
    btn.type = "button";
    btn.dataset.letter = letter;
    btn.disabled = !volunteers.some((v) => matchesLetter(v.name, letter));
    bar.appendChild(btn);
  }
}

function renderNames() {
  const grid = document.getElementById("name-grid");
  grid.replaceChildren();
  const list = filteredVolunteers();
  if (!list.length) {
    grid.appendChild(el("p", "empty-msg",
      volunteers.length ? "No matching names. Tap “Not on the list?” below." : "No volunteers have been added yet."));
    return;
  }
  for (const v of list) {
    const btn = el("button", "name-btn", v.name);
    btn.type = "button";
    btn.dataset.id = v.id;
    grid.appendChild(btn);
  }
}

function renderActivities() {
  const grid = document.getElementById("activity-grid");
  grid.replaceChildren();
  for (const a of activities) {
    const btn = el("button", "activity-btn", a.name);
    btn.type = "button";
    btn.dataset.id = a.id;
    grid.appendChild(btn);
  }
}

function renderHomeActivity() {
  const a = resolveLockedActivity();
  document.getElementById("home-activity").textContent = a ? `Checking in for: ${a.name}` : "";
}

function renderClock() {
  const now = new Date();
  document.getElementById("home-clock").textContent =
    now.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" }) +
    " · " + now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

// ── Check-in flow ────────────────────────────────────────────────────────────

function resolveLockedActivity() {
  if (lockedActivity) {
    const match = activities.find(
      (a) => a.id === lockedActivity || a.name.toLowerCase() === lockedActivity.toLowerCase()
    );
    return match || { id: "", name: lockedActivity };
  }
  if (activities.length === 1) return activities[0];
  if (activities.length === 0) return { id: "", name: "General" };
  return null; // Ask the volunteer.
}

function selectVolunteer(volunteer) {
  pendingVolunteer = volunteer;
  const activity = resolveLockedActivity();
  if (activity) {
    checkIn(activity);
    return;
  }
  document.getElementById("activity-title").textContent =
    `Hi ${firstName(volunteer.name)}! What are you checking in for?`;
  renderActivities();
  show("activity");
}

function firstName(name) {
  return name.split(/\s+/)[0] || name;
}

function checkIn(activity) {
  const v = pendingVolunteer;
  if (!v) return;
  pendingVolunteer = null;

  const now = new Date();
  const entry = { checked_in_at: now.toISOString() };
  if (v.id) entry.volunteer_id = v.id;
  else entry.name = v.name;
  if (activity.id) entry.activity_id = activity.id;
  else entry.activity = activity.name;

  const queue = readJSON(LS_QUEUE, []);
  queue.push(entry);
  localStorage.setItem(LS_QUEUE, JSON.stringify(queue));
  flushQueue();

  document.getElementById("welcome-name").textContent = `Welcome, ${firstName(v.name)}!`;
  document.getElementById("welcome-detail").textContent =
    `Checked in for ${activity.name} at ${now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
  show("welcome");
  welcomeTimer = setTimeout(goHome, WELCOME_MS);
}

let flushing = false;

async function flushQueue() {
  if (flushing) return;
  flushing = true;
  try {
    let queue = readJSON(LS_QUEUE, []);
    while (queue.length) {
      const entry = queue[0];
      let r;
      try {
        r = await fetch(`${API_BASE_URL}/checkin`, {
          method: "POST",
          headers: headers(),
          body: JSON.stringify(entry),
        });
      } catch {
        break; // Offline — try again later.
      }
      // 5xx: server trouble, retry later. 4xx: bad entry (e.g. removed from
      // roster) — drop it so it can't block the rest of the queue.
      if (r.status >= 500) break;
      queue = readJSON(LS_QUEUE, []);
      queue.shift();
      localStorage.setItem(LS_QUEUE, JSON.stringify(queue));
    }
  } finally {
    flushing = false;
    renderSyncStatus();
  }
}

function renderSyncStatus() {
  const n = readJSON(LS_QUEUE, []).length;
  document.getElementById("sync-status").textContent =
    n ? `${n} check-in${n === 1 ? "" : "s"} waiting to sync…` : "";
}

// ── Events ───────────────────────────────────────────────────────────────────

document.getElementById("start-btn").addEventListener("click", goNames);
document.getElementById("done-btn").addEventListener("click", goHome);
document.getElementById("retry-btn").addEventListener("click", loadData);
document.getElementById("walkin-btn").addEventListener("click", () => {
  document.getElementById("walkin-name").value = "";
  show("walkin");
  document.getElementById("walkin-name").focus();
});

document.querySelectorAll("[data-go]").forEach((btn) =>
  btn.addEventListener("click", () => (btn.dataset.go === "names" ? goNames() : goHome()))
);

document.getElementById("name-search").addEventListener("input", () => {
  activeLetter = "";
  renderLetters();
  renderNames();
});

document.getElementById("letter-bar").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-letter]");
  if (!btn) return;
  activeLetter = activeLetter === btn.dataset.letter ? "" : btn.dataset.letter;
  document.getElementById("name-search").value = "";
  renderLetters();
  renderNames();
});

document.getElementById("name-grid").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-id]");
  if (!btn) return;
  const v = volunteers.find((x) => x.id === btn.dataset.id);
  if (v) selectVolunteer(v);
});

document.getElementById("activity-grid").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-id]");
  if (!btn) return;
  const a = activities.find((x) => x.id === btn.dataset.id);
  if (a) checkIn(a);
});

document.getElementById("walkin-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const name = document.getElementById("walkin-name").value.replace(/\s+/g, " ").trim();
  if (!name) return;
  document.getElementById("walkin-name").blur();
  selectVolunteer({ id: "", name });
});

// Any touch on a non-home screen keeps it from timing out.
["pointerdown", "keydown", "input"].forEach((evt) =>
  document.addEventListener(evt, () => {
    if (idleTimer && !document.getElementById("screen-home").classList.contains("active")) resetIdle();
  })
);

window.addEventListener("online", flushQueue);

// ── Start ────────────────────────────────────────────────────────────────────

// Launched straight onto the name list with nowhere to go back to: hide Back.
if (startOnNames && !returnUrl) {
  document.querySelector("#screen-names .back-btn").style.visibility = "hidden";
}

if (typeof ORG_NAME !== "undefined" && ORG_NAME) {
  document.getElementById("org-name").textContent = ORG_NAME;
  document.getElementById("welcome-thanks").textContent = `Thank you for volunteering with ${ORG_NAME}!`;
}

renderClock();
setInterval(renderClock, 15000);
loadData().then(() => {
  if (startOnNames && !document.getElementById("screen-error").classList.contains("active")) goNames();
});
flushQueue();
setInterval(flushQueue, FLUSH_MS);
setInterval(() => {
  // Pick up roster changes, but never yank the list out from under someone.
  const names = document.getElementById("screen-names").classList.contains("active");
  const idleOnList = startOnNames && names && !document.getElementById("name-search").value && !activeLetter;
  if (document.getElementById("screen-home").classList.contains("active") || idleOnList) loadData();
}, REFRESH_MS);
