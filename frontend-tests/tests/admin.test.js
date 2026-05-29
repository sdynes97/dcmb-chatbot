/**
 * Tests for admin.js UI logic.
 */

beforeEach(() => {
  document.body.innerHTML = `
    <section id="auth-section">
      <form id="auth-form">
        <input id="api-key" type="text" />
        <button type="submit">Sign In</button>
      </form>
    </section>
    <div id="admin-section" style="display:none">
      <p id="eta-status"></p>
      <form id="eta-form">
        <input name="eta_message" id="eta_message" />
        <input name="eta_time" id="eta_time" type="time" />
        <button type="submit">Post</button>
      </form>
      <button id="clear-eta-btn">Clear ETA</button>
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
        <button type="submit">Save</button>
      </form>
    </div>
    <div id="message" class="msg"></div>
  `;
  globalThis.API_BASE_URL = "http://localhost:7071/api";
  globalThis.fetch = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("auth form shows admin section on valid key", async () => {
  fetch
    .mockResolvedValueOnce({ status: 200, json: async () => [] })   // GET /admin/events
    .mockResolvedValueOnce({ ok: true, json: async () => ({ eta: null }) }); // GET /location

  await import("../../frontend/js/admin.js");

  document.getElementById("api-key").value = "my-key";
  document.getElementById("auth-form").dispatchEvent(new Event("submit"));

  await vi.waitFor(() => {
    expect(document.getElementById("admin-section").style.display).not.toBe("none");
  });
});

test("auth form shows error on 401", async () => {
  fetch.mockResolvedValueOnce({ status: 401, json: async () => [] });

  await import("../../frontend/js/admin.js");

  document.getElementById("api-key").value = "wrong-key";
  document.getElementById("auth-form").dispatchEvent(new Event("submit"));

  await vi.waitFor(() => {
    const msg = document.getElementById("message");
    expect(msg.textContent).toMatch(/Invalid API key/);
  });
});
