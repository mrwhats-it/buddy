const BACKEND_BASE = "http://localhost:8420";

async function backendRequest(path, options = {}) {
  const resp = await fetch(`${BACKEND_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `Backend error: ${resp.status}`);
  }
  return resp.json();
}

const BuddyBackend = {
  health: () => backendRequest("/health"),
  getConfig: () => backendRequest("/config"),
  setConfig: (update) =>
    backendRequest("/config", { method: "POST", body: JSON.stringify(update) }),
  save: (payload) =>
    backendRequest("/save", { method: "POST", body: JSON.stringify(payload) }),
  search: (query, limit = 8) =>
    backendRequest("/search", { method: "POST", body: JSON.stringify({ query, limit }) }),
  chat: (messages) =>
    backendRequest("/chat", { method: "POST", body: JSON.stringify({ messages }) }),
  title: (prompt) =>
    backendRequest("/title", { method: "POST", body: JSON.stringify({ prompt }) }),
};
