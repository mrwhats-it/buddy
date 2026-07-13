const STORAGE_KEY = "buddy_threads";
const UI_KEY = "buddy_ui";

let state = { threads: [], activeId: null };
let ui = { sidebarCollapsed: false };
let sending = false;
let renamingId = null;

if (typeof marked !== "undefined") {
  marked.setOptions({ gfm: true, breaks: true });
}

function isEmpty(thread) {
  return thread && thread.messages.length === 0;
}

function newThread() {
  const btn = document.getElementById("new-thread");
  if (btn) btn.blur();

  const active = activeThread();
  if (isEmpty(active)) {
    document.getElementById("input").focus();
    return;
  }
  const existingEmpty = state.threads.find(isEmpty);
  if (existingEmpty) {
    state.activeId = existingEmpty.id;
    render();
    document.getElementById("input").focus();
    return;
  }

  const id = crypto.randomUUID();
  const thread = { id, title: "New chat", messages: [] };
  state.threads.unshift(thread);
  state.activeId = id;
  persist();
  render();
  document.getElementById("input").focus();
}

function activeThread() {
  return state.threads.find((t) => t.id === state.activeId);
}

async function persist() {
  await chrome.storage.local.set({ [STORAGE_KEY]: state });
}

async function persistUi() {
  await chrome.storage.local.set({ [UI_KEY]: ui });
}

async function restore() {
  const data = await chrome.storage.local.get([STORAGE_KEY, UI_KEY]);
  if (data[STORAGE_KEY]?.threads?.length) {
    state = data[STORAGE_KEY];
  } else {
    const id = crypto.randomUUID();
    state.threads.unshift({ id, title: "New chat", messages: [] });
    state.activeId = id;
    await persist();
  }
  if (data[UI_KEY]) ui = { ...ui, ...data[UI_KEY] };
  applyUi();
}

function applyUi() {
  document.body.classList.toggle("sidebar-collapsed", ui.sidebarCollapsed);
  const btn = document.getElementById("collapse-sidebar");
  if (btn) btn.title = ui.sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar";
}

function renderThreadList() {
  const list = document.getElementById("thread-list");
  list.innerHTML = "";
  for (const t of state.threads) {
    const li = document.createElement("li");
    li.className = t.id === state.activeId ? "active" : "";
    li.dataset.threadId = t.id;

    if (renamingId === t.id) {
      const inp = document.createElement("input");
      inp.className = "thread-rename";
      inp.value = t.title;
      inp.addEventListener("blur", () => commitRename(t.id, inp.value));
      inp.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { e.preventDefault(); inp.blur(); }
        else if (e.key === "Escape") { renamingId = null; render(); }
      });
      li.appendChild(inp);
      setTimeout(() => { inp.focus(); inp.select(); }, 0);
    } else {
      const title = document.createElement("span");
      title.className = "thread-title";
      title.textContent = t.title;
      li.appendChild(title);

      li.addEventListener("click", () => {
        state.activeId = t.id;
        render();
      });
      li.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        state.activeId = t.id;
        openContextMenu(e.clientX, e.clientY, t.id);
      });
    }

    list.appendChild(li);
  }
}

function commitRename(id, newTitle) {
  const t = state.threads.find((x) => x.id === id);
  if (t) {
    const trimmed = newTitle.trim();
    if (trimmed) t.title = trimmed.slice(0, 60);
  }
  renamingId = null;
  persist();
  render();
}

function deleteThread(id) {
  state.threads = state.threads.filter((t) => t.id !== id);
  if (state.activeId === id) state.activeId = state.threads[0]?.id || null;
  if (state.threads.length === 0) {
    newThread();
    return;
  }
  persist();
  render();
}

/* ---------- Context menu ---------- */

let contextTarget = null;

function openContextMenu(x, y, threadId) {
  contextTarget = threadId;
  const menu = document.getElementById("context-menu");
  menu.hidden = false;
  // Position after unhide so we can measure width/height.
  const { innerWidth: w, innerHeight: h } = window;
  const rect = menu.getBoundingClientRect();
  const left = Math.min(x, w - rect.width - 4);
  const top = Math.min(y, h - rect.height - 4);
  menu.style.left = `${left}px`;
  menu.style.top = `${top}px`;
}

function closeContextMenu() {
  const menu = document.getElementById("context-menu");
  menu.hidden = true;
  contextTarget = null;
}

/* ---------- Rendering ---------- */

function renderBubbleContent(bubble, role, content) {
  if (role === "assistant" && typeof marked !== "undefined") {
    bubble.innerHTML = marked.parse(content);
  } else {
    bubble.textContent = content;
  }
}

function renderMessages() {
  const container = document.getElementById("messages");
  container.innerHTML = "";
  const thread = activeThread();
  if (!thread) return;

  if (thread.messages.length === 0 && !sending) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "Ask about anything you've saved.";
    container.appendChild(empty);
    return;
  }

  for (const m of thread.messages) {
    const wrap = document.createElement("div");
    wrap.className = `msg msg-${m.role}`;
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    renderBubbleContent(bubble, m.role, m.content);
    wrap.appendChild(bubble);
    container.appendChild(wrap);
  }

  if (sending) {
    const wrap = document.createElement("div");
    wrap.className = "msg msg-assistant";
    const bubble = document.createElement("div");
    bubble.className = "bubble typing";
    bubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    wrap.appendChild(bubble);
    container.appendChild(wrap);
  }

  container.scrollTop = container.scrollHeight;
}

function setSending(isSending) {
  sending = isSending;
  document.getElementById("send").disabled = isSending;
  document.getElementById("input").disabled = isSending;
}

function render() {
  renderThreadList();
  renderMessages();
}

/* ---------- Send ---------- */

async function sendMessage() {
  if (sending) return;
  const input = document.getElementById("input");
  const text = input.value.trim();
  if (!text) return;

  const thread = activeThread();
  const isFirstMessage = thread.messages.length === 0;
  thread.messages.push({ role: "user", content: text });
  // Provisional fallback title in case the title endpoint fails.
  if (thread.title === "New chat") thread.title = text.slice(0, 30);
  input.value = "";
  autoResize(input);
  setSending(true);
  render();
  await persist();

  // Fire the chat request and (if it's the first message) the title request in
  // parallel — the title endpoint is cheap and we don't want to slow down the
  // real reply waiting for a name.
  const messagesPayload = thread.messages.map(({ role, content }) => ({ role, content }));
  const chatPromise = BuddyBackend.chat(messagesPayload);
  const titlePromise = isFirstMessage ? BuddyBackend.title(text).catch(() => null) : null;

  try {
    const { reply } = await chatPromise;
    thread.messages.push({ role: "assistant", content: reply });
  } catch (err) {
    thread.messages.push({
      role: "assistant",
      content: `(Error: ${err.message}. Is the Buddy backend running? Try "buddy start".)`,
    });
  }
  setSending(false);
  render();
  await persist();
  input.focus();

  if (titlePromise) {
    const result = await titlePromise;
    if (result?.title && thread.messages.length > 0) {
      thread.title = result.title;
      await persist();
      renderThreadList();
    }
  }
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 140) + "px";
}

/* ---------- Wire-up ---------- */

document.getElementById("new-thread").addEventListener("click", newThread);
document.getElementById("collapse-sidebar").addEventListener("click", (e) => {
  e.currentTarget.blur();
  ui.sidebarCollapsed = !ui.sidebarCollapsed;
  applyUi();
  persistUi();
});
document.getElementById("send").addEventListener("click", (e) => {
  e.currentTarget.blur();
  sendMessage();
});

const inputEl = document.getElementById("input");
inputEl.addEventListener("input", () => autoResize(inputEl));
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

document.getElementById("context-menu").addEventListener("click", (e) => {
  const action = e.target.closest("button")?.dataset.action;
  if (!action || !contextTarget) return;
  const id = contextTarget;
  closeContextMenu();
  if (action === "rename") {
    renamingId = id;
    render();
  } else if (action === "delete") {
    deleteThread(id);
  }
});

document.addEventListener("click", (e) => {
  const menu = document.getElementById("context-menu");
  if (!menu.hidden && !menu.contains(e.target)) closeContextMenu();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeContextMenu();
});
window.addEventListener("blur", closeContextMenu);

restore().then(render);
