const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");

// Conversation history sent with each request for context
let history = [];

const SUGGESTIONS = [
  "When is the next performance?",
  "What time is call time?",
  "Where do I pick up my kid?",
  "What's the ETA tonight?",
];

function appendMessage(text, role) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function showTyping() {
  return appendMessage("Typing…", "typing");
}

async function sendMessage(text) {
  text = text.trim();
  if (!text) return;

  appendMessage(text, "user");
  chatInput.value = "";
  sendBtn.disabled = true;

  const typing = showTyping();

  try {
    const resp = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history }),
    });

    const data = await resp.json();
    typing.remove();

    if (!resp.ok || data.error) {
      appendMessage(data.error || "Something went wrong. Please try again.", "error");
      return;
    }

    appendMessage(data.reply, "bot");
    history.push({ role: "user", content: text });
    history.push({ role: "assistant", content: data.reply });
    // Keep last 10 turns to avoid bloating the prompt
    if (history.length > 20) history = history.slice(-20);
  } catch (err) {
    typing.remove();
    appendMessage("Network error. Please check your connection and try again.", "error");
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(chatInput.value);
});

// Render suggestion chips
const suggestionsDiv = document.getElementById("suggestions");
if (suggestionsDiv) {
  SUGGESTIONS.forEach((s) => {
    const btn = document.createElement("button");
    btn.className = "suggestion-btn";
    btn.textContent = s;
    btn.addEventListener("click", () => sendMessage(s));
    suggestionsDiv.appendChild(btn);
  });
}

// Welcome message
appendMessage(
  "Hi! I'm the DCMB Info Bot. Ask me about the band schedule, call times, performance times, or bus return ETA.",
  "bot"
);
