/**
 * Tests for kiosk.js — the iPad volunteer check-in flow.
 * The DOM fixture mirrors the elements kiosk.js queries in index.html.
 */

const KIOSK_DATA = {
  volunteers: [
    { id: "v1", name: "Jane Smith" },
    { id: "v2", name: "Bob Adams" },
  ],
  activities: [
    { id: "a1", name: "Concessions" },
    { id: "a2", name: "Pit Crew" },
  ],
};

function mockFetch(data = KIOSK_DATA) {
  fetch.mockImplementation((url) => {
    if (url.includes("/kiosk")) {
      return Promise.resolve({ ok: true, status: 200, json: async () => data });
    }
    return Promise.resolve({ ok: true, status: 200, json: async () => ({ status: "ok" }) });
  });
}

const active = () => document.querySelector(".screen.active").id;
const checkinCalls = () => fetch.mock.calls.filter(([url]) => url.includes("/checkin"));

beforeEach(() => {
  vi.resetModules();
  vi.useFakeTimers({ shouldAdvanceTime: true });
  localStorage.clear();
  document.body.innerHTML = `
    <section id="screen-home" class="screen active">
      <h1 id="org-name"></h1><div id="home-clock"></div><div id="home-activity"></div>
      <button id="start-btn"></button><div id="sync-status"></div>
    </section>
    <section id="screen-names" class="screen">
      <button class="back-btn" data-go="home"></button>
      <input type="search" id="name-search" />
      <div id="letter-bar"></div><div id="name-grid"></div>
      <button id="walkin-btn"></button>
    </section>
    <section id="screen-walkin" class="screen">
      <button class="back-btn" data-go="names"></button>
      <form id="walkin-form"><input id="walkin-name" /><button type="submit"></button></form>
    </section>
    <section id="screen-activity" class="screen">
      <button class="back-btn" data-go="names"></button>
      <h2 id="activity-title"></h2><div id="activity-grid"></div>
    </section>
    <section id="screen-welcome" class="screen">
      <h1 id="welcome-name"></h1><p id="welcome-detail"></p><p id="welcome-thanks"></p><button id="done-btn"></button>
    </section>
    <section id="screen-error" class="screen">
      <p id="error-detail"></p><button id="retry-btn"></button>
    </section>
  `;
  globalThis.API_BASE_URL = "http://localhost:7071/api";
  globalThis.ORG_NAME = "Test Band";
  history.replaceState(null, "", "/");
  globalThis.fetch = vi.fn();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

async function loadKiosk() {
  await import("../../frontend/js/kiosk.js");
  await vi.waitFor(() => expect(document.querySelectorAll(".name-btn").length).toBe(2));
}

test("name → activity → welcome → back home, and the check-in is posted", async () => {
  mockFetch();
  await loadKiosk();

  document.getElementById("start-btn").click();
  expect(active()).toBe("screen-names");

  document.querySelector(".name-btn[data-id='v1']").click();
  expect(active()).toBe("screen-activity");
  expect(document.getElementById("activity-title").textContent).toMatch(/Hi Jane/);

  document.querySelector(".activity-btn[data-id='a2']").click();
  expect(active()).toBe("screen-welcome");
  expect(document.getElementById("welcome-name").textContent).toBe("Welcome, Jane!");
  expect(document.getElementById("welcome-detail").textContent).toMatch(/Pit Crew/);

  await vi.waitFor(() => expect(checkinCalls().length).toBe(1));
  const body = JSON.parse(checkinCalls()[0][1].body);
  expect(body).toMatchObject({ volunteer_id: "v1", activity_id: "a2" });
  expect(body.checked_in_at).toBeTruthy();

  vi.advanceTimersByTime(5000);
  expect(active()).toBe("screen-home");
});

test("single activity skips the picker", async () => {
  mockFetch({ ...KIOSK_DATA, activities: [{ id: "a1", name: "Concessions" }] });
  await loadKiosk();

  document.getElementById("start-btn").click();
  document.querySelector(".name-btn[data-id='v2']").click();
  expect(active()).toBe("screen-welcome");
});

test("search filters the name list", async () => {
  mockFetch();
  await loadKiosk();

  const search = document.getElementById("name-search");
  search.value = "adam";
  search.dispatchEvent(new Event("input"));
  const names = [...document.querySelectorAll(".name-btn")].map((b) => b.textContent);
  expect(names).toEqual(["Bob Adams"]);
});

test("walk-in sends a typed name", async () => {
  mockFetch({ ...KIOSK_DATA, activities: [] });
  await loadKiosk();

  document.getElementById("walkin-btn").click();
  document.getElementById("walkin-name").value = "  New   Person ";
  document.getElementById("walkin-form").dispatchEvent(new Event("submit"));

  expect(active()).toBe("screen-welcome");
  await vi.waitFor(() => expect(checkinCalls().length).toBe(1));
  expect(JSON.parse(checkinCalls()[0][1].body)).toMatchObject({ name: "New Person", activity: "General" });
});

test("check-ins made offline stay queued", async () => {
  mockFetch();
  await loadKiosk();
  fetch.mockImplementation(() => Promise.reject(new TypeError("offline")));

  document.getElementById("start-btn").click();
  document.querySelector(".name-btn[data-id='v1']").click();
  document.querySelector(".activity-btn[data-id='a1']").click();

  await vi.waitFor(() =>
    expect(document.getElementById("sync-status").textContent).toMatch(/1 check-in waiting/)
  );
  expect(JSON.parse(localStorage.getItem("vc_kiosk_queue"))).toHaveLength(1);
});

test("idle screen returns home", async () => {
  mockFetch();
  await loadKiosk();

  document.getElementById("start-btn").click();
  vi.advanceTimersByTime(45000);
  expect(active()).toBe("screen-home");
});

test("shows the org name from config", async () => {
  mockFetch();
  await loadKiosk();
  expect(document.getElementById("org-name").textContent).toBe("Test Band");
});

test("?start=names launches straight onto the name list and returns there", async () => {
  history.replaceState(null, "", "/?start=names&activity=Concessions");
  mockFetch();
  await loadKiosk();
  await vi.waitFor(() => expect(active()).toBe("screen-names"));
  expect(document.querySelector("#screen-names .back-btn").style.visibility).toBe("hidden");

  document.querySelector(".name-btn[data-id='v1']").click();
  expect(active()).toBe("screen-welcome");
  await vi.waitFor(() => expect(checkinCalls().length).toBe(1));
  expect(JSON.parse(checkinCalls()[0][1].body)).toMatchObject({ activity_id: "a1" });

  vi.advanceTimersByTime(5000);
  expect(active()).toBe("screen-names");
});
