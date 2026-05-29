/**
 * Tests for chat.js UI logic.
 * We test the pure JS functions by importing them in isolation.
 */

// Mock the DOM elements that chat.js expects
beforeEach(() => {
  // Force chat.js to re-run its top-level code against the fresh DOM below.
  vi.resetModules();
  document.body.innerHTML = `
    <div id="chat-window"></div>
    <form id="chat-form">
      <input id="chat-input" type="text" />
      <button id="send-btn" type="submit">Send</button>
    </form>
    <div id="suggestions"></div>
  `;
  globalThis.API_BASE_URL = "http://localhost:7071/api";
  globalThis.fetch = vi.fn();
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("suggestion buttons are rendered", async () => {
  await import("../../frontend/js/chat.js");
  const buttons = document.querySelectorAll(".suggestion-btn");
  expect(buttons.length).toBeGreaterThan(0);
});

test("welcome message is shown on load", async () => {
  await import("../../frontend/js/chat.js");
  const messages = document.querySelectorAll(".message.bot");
  expect(messages.length).toBeGreaterThan(0);
  expect(messages[0].textContent).toMatch(/DCMB Info Bot/);
});

test("chat form submit sends fetch request", async () => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ reply: "Game is Sept 6 at 7pm." }),
  });

  await import("../../frontend/js/chat.js");

  const input = document.getElementById("chat-input");
  input.value = "When is the next game?";
  document.getElementById("chat-form").dispatchEvent(new Event("submit"));

  await vi.waitFor(() => {
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:7071/api/chat",
      expect.objectContaining({ method: "POST" })
    );
  });
});

test("error response shows error message", async () => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: false,
    json: async () => ({ error: "Something went wrong." }),
  });

  await import("../../frontend/js/chat.js");

  const input = document.getElementById("chat-input");
  input.value = "Hello?";
  document.getElementById("chat-form").dispatchEvent(new Event("submit"));

  await vi.waitFor(() => {
    const errors = document.querySelectorAll(".message.error");
    expect(errors.length).toBeGreaterThan(0);
  });
});
