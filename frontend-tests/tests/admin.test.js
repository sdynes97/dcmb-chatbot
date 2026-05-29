/**
 * Tests for admin.js UI logic.
 * The DOM fixture below mirrors the elements admin.js queries at load time.
 */

beforeEach(() => {
  // Force admin.js to re-run its top-level code against the fresh DOM below.
  vi.resetModules();
  localStorage.clear();
  document.body.innerHTML = `
    <div id="toast"></div>

    <div class="card" id="auth-card">
      <form id="auth-form">
        <input type="password" id="api-key" />
        <input type="checkbox" id="remember-me" checked />
        <button type="submit">Sign In</button>
      </form>
    </div>

    <div id="admin-content" style="display:none">
      <button id="logout-btn">Sign Out</button>

      <div id="eta-current" class="eta-current none"></div>
      <div id="tracking-status"></div>
      <button id="start-tracking-btn">Start</button>
      <button id="stop-tracking-btn" style="display:none">Stop</button>
      <form id="eta-form">
        <input name="eta_message" id="eta_message" />
        <input name="eta_time" id="eta_time" type="time" />
        <button type="submit">Post</button>
      </form>
      <button id="clear-eta-btn">Clear ETA</button>

      <div id="mobile-events-list"></div>
      <table><tbody id="events-tbody"></tbody></table>

      <form id="event-form">
        <input id="event_name" name="event_name" />
        <select id="event_type" name="event_type">
          <option value="football_game">Football</option>
        </select>
        <input id="event_date" name="event_date" type="date" />
        <input id="call_time" name="call_time" type="time" />
        <input id="performance_time" name="performance_time" type="time" />
        <input id="estimated_return" name="estimated_return" type="time" />
        <input id="location_name" name="location_name" />
        <input id="location_address" name="location_address" />
        <input id="drop_off_location" name="drop_off_location" />
        <textarea id="notes" name="notes"></textarea>
        <input id="is_away" name="is_away" type="checkbox" />
        <input id="partition_key" name="partition_key" type="hidden" />
        <input id="row_key" name="row_key" type="hidden" />
        <button type="submit" id="save-event-btn">Save</button>
        <button type="button" id="cancel-edit-btn" style="display:none">Cancel</button>
        <h2 id="event-form-title">Add Event</h2>
      </form>
    </div>
  `;
  globalThis.API_BASE_URL = "http://localhost:7071/api";
  globalThis.fetch = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("valid key reveals admin content", async () => {
  fetch.mockImplementation((url) => {
    if (url.includes("/admin/events")) {
      return Promise.resolve({ ok: true, status: 200, json: async () => [] });
    }
    // GET /location
    return Promise.resolve({ ok: true, json: async () => ({ eta: null }) });
  });

  await import("../../frontend/js/admin.js");

  document.getElementById("api-key").value = "my-key";
  document.getElementById("auth-form").dispatchEvent(new Event("submit"));

  await vi.waitFor(() => {
    expect(document.getElementById("admin-content").style.display).toBe("block");
  });
});

test("invalid key shows error toast and stays signed out", async () => {
  fetch.mockResolvedValueOnce({ ok: false, status: 401, json: async () => [] });

  await import("../../frontend/js/admin.js");

  document.getElementById("api-key").value = "wrong-key";
  document.getElementById("auth-form").dispatchEvent(new Event("submit"));

  await vi.waitFor(() => {
    expect(document.getElementById("toast").textContent).toMatch(/Invalid access key/);
  });
  expect(document.getElementById("admin-content").style.display).toBe("none");
});

test("remembered key auto signs in on load", async () => {
  localStorage.setItem("dcmb_admin_key", "saved-key");
  fetch.mockImplementation((url) => {
    if (url.includes("/admin/events")) {
      return Promise.resolve({ ok: true, status: 200, json: async () => [] });
    }
    return Promise.resolve({ ok: true, json: async () => ({ eta: null }) });
  });

  await import("../../frontend/js/admin.js");

  await vi.waitFor(() => {
    expect(document.getElementById("admin-content").style.display).toBe("block");
  });
});
