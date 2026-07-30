const messages = document.getElementById("messages");
const composer = document.getElementById("composer");
const input = document.getElementById("input");
const send = document.getElementById("send");
const newChat = document.getElementById("new-chat");
const subtitle = document.getElementById("subtitle");
const guardrails = document.getElementById("guardrails");

let conversationId = crypto.randomUUID();
let stream = null;

fetch("/api/config")
  .then((r) => r.json())
  .then((cfg) => {
    subtitle.textContent = `Answering questions about ${cfg.target_repo}`;
    guardrails.textContent = `read-only · ${cfg.allowed_tools.length} tools · max ${cfg.max_turns} turns`;
  })
  .catch(() => {});

function scroll() {
  messages.scrollTop = messages.scrollHeight;
}

function addMessage(text, role) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (role === "assistant") {
    bubble.innerHTML = renderMarkdown(text);
  } else {
    bubble.textContent = text;
  }
  wrapper.append(bubble);
  messages.append(wrapper);
  scroll();
  return wrapper;
}

// Live feed of the agent's tool calls, appended to as SSE events arrive.
function addActivityFeed() {
  const feed = document.createElement("div");
  feed.className = "activity";
  feed.innerHTML = "<div>thinking</div>";
  messages.append(feed);
  scroll();
  return {
    push(detail) {
      feed.innerHTML = "";
      const line = document.createElement("div");
      line.textContent = detail;
      feed.append(line);
      scroll();
    },
    finish() {
      feed.classList.add("done");
      if (!feed.textContent.trim()) feed.remove();
    },
  };
}

function escapeHtml(text) {
  return text.replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
}

// Deliberately tiny: escape everything first, then re-introduce the handful of
// Markdown constructs the agent actually uses.
function renderMarkdown(text) {
  return escapeHtml(text)
    .replace(/```(\w*)\n([\s\S]*?)```/g, (_, _lang, code) => `<pre><code>${code}</code></pre>`)
    .replace(/`([^`\n]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
    .replace(/^(\s*)[-*] /gm, "$1• ");
}

function setBusy(busy) {
  send.disabled = busy;
  input.disabled = busy;
  if (!busy) input.focus();
}

function ask(message) {
  addMessage(message, "user");
  const feed = addActivityFeed();
  setBusy(true);

  const url = `/api/chat/stream?message=${encodeURIComponent(message)}&conversation_id=${encodeURIComponent(conversationId)}`;
  stream = new EventSource(url);

  const settle = (text, role) => {
    feed.finish();
    addMessage(text, role);
    stream.close();
    stream = null;
    setBusy(false);
  };

  stream.addEventListener("activity", (e) => feed.push(JSON.parse(e.data).detail));
  stream.addEventListener("reply", (e) => settle(JSON.parse(e.data).reply, "assistant"));
  stream.addEventListener("error", (e) => {
    if (e.data) {
      settle(JSON.parse(e.data).reply, "assistant error");
    } else if (stream) {
      settle("Lost the connection to the server. Is it still running?", "assistant error");
    }
  });
}

composer.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  ask(message);
});

newChat.addEventListener("click", async () => {
  if (stream) stream.close();
  await fetch("/api/chat/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId }),
  }).catch(() => {});
  conversationId = crypto.randomUUID();
  messages.innerHTML = "";
  addMessage("New conversation. The agent has forgotten what we discussed.", "assistant");
  setBusy(false);
});
