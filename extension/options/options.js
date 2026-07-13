const statusEl = document.getElementById("status");

// Base URLs for known providers. Kept in sync with backend/buddy/config.py.
const PROVIDER_BASE_URLS = {
  groq: "https://api.groq.com/openai/v1",
  openai: "https://api.openai.com/v1",
  anthropic: "https://api.anthropic.com/v1",
  gemini: "https://generativelanguage.googleapis.com/v1beta/openai",
  ollama: "http://localhost:11434/v1",
};

// Curated model catalogs. Left value is the API model ID, right is the label
// shown in the dropdown. Groq's IDs are namespaced (e.g. "openai/gpt-oss-120b"),
// so a plain text input is easy to get wrong — hence the dropdown.
const PROVIDER_MODELS = {
  groq: [
    { id: "openai/gpt-oss-120b", label: "GPT-OSS 120B" },
    { id: "openai/gpt-oss-20b", label: "GPT-OSS 20B" },
    { id: "moonshotai/kimi-k2-instruct", label: "Kimi K2 Instruct" },
    { id: "meta-llama/llama-4-scout-17b-16e-instruct", label: "Llama 4 Scout 17B" },
    { id: "meta-llama/llama-4-maverick-17b-128e-instruct", label: "Llama 4 Maverick 17B" },
    { id: "llama-3.3-70b-versatile", label: "Llama 3.3 70B Versatile" },
    { id: "llama-3.1-8b-instant", label: "Llama 3.1 8B Instant" },
    { id: "qwen/qwen3-32b", label: "Qwen3 32B" },
    { id: "deepseek-r1-distill-llama-70b", label: "DeepSeek R1 Distill Llama 70B" },
    { id: "mistral-saba-24b", label: "Mistral Saba 24B" },
  ],
};

const providerEl = document.getElementById("provider");
const baseUrlEl = document.getElementById("llm_base_url");
const modelInputEl = document.getElementById("llm_model");
const modelSelectEl = document.getElementById("llm_model_select");
const modelInputLabel = document.getElementById("model_input_label");
const modelSelectLabel = document.getElementById("model_select_label");

function renderModelChooser(currentModel) {
  const provider = providerEl.value;
  const models = PROVIDER_MODELS[provider];
  if (!models) {
    modelInputLabel.style.display = "";
    modelSelectLabel.style.display = "none";
    return;
  }

  modelSelectEl.innerHTML = "";
  let matched = false;
  for (const { id, label } of models) {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = `${label}  (${id})`;
    if (id === currentModel) {
      opt.selected = true;
      matched = true;
    }
    modelSelectEl.appendChild(opt);
  }
  // Escape hatch: let the user type a model not in the curated list.
  const customOpt = document.createElement("option");
  customOpt.value = "__custom__";
  customOpt.textContent = "Other (type it in)…";
  if (!matched && currentModel) customOpt.selected = true;
  modelSelectEl.appendChild(customOpt);

  modelInputLabel.style.display = modelSelectEl.value === "__custom__" ? "" : "none";
  modelSelectLabel.style.display = "";
}

providerEl.addEventListener("change", () => {
  const url = PROVIDER_BASE_URLS[providerEl.value];
  if (url) baseUrlEl.value = url;
  renderModelChooser(modelInputEl.value);
});

modelSelectEl.addEventListener("change", () => {
  if (modelSelectEl.value === "__custom__") {
    modelInputLabel.style.display = "";
    modelInputEl.focus();
  } else {
    modelInputEl.value = modelSelectEl.value;
    modelInputLabel.style.display = "none";
  }
});

function resolveModel() {
  const provider = providerEl.value;
  const models = PROVIDER_MODELS[provider];
  if (!models) return modelInputEl.value.trim();
  if (modelSelectEl.value === "__custom__") return modelInputEl.value.trim();
  return modelSelectEl.value;
}

function inferProviderFromBaseUrl(baseUrl) {
  if (!baseUrl) return "";
  for (const [name, url] of Object.entries(PROVIDER_BASE_URLS)) {
    if (baseUrl.trim() === url) return name;
  }
  return "";
}

async function refreshStatus() {
  try {
    const health = await BuddyBackend.health();
    statusEl.className = health.supermemory === "ok" ? "ok" : "bad";
    statusEl.textContent =
      health.supermemory === "ok"
        ? `Backend running. Supermemory connected. LLM configured: ${health.llm_configured}`
        : health.supermemory_guidance || "Backend running, but supermemory isn't ready yet.";
  } catch (err) {
    statusEl.className = "bad";
    statusEl.textContent =
      "Buddy backend is not running.\n\nOpen a terminal and run:\n  buddy start\n\n(If you haven't installed it yet: pip install -e backend/)";
  }
}

async function loadConfig() {
  try {
    const cfg = await BuddyBackend.getConfig();
    document.getElementById("supermemory_url").value = cfg.supermemory_url || "";
    baseUrlEl.value = cfg.llm_base_url || "";
    modelInputEl.value = cfg.llm_model || "";
    providerEl.value = cfg.provider || inferProviderFromBaseUrl(cfg.llm_base_url);
    renderModelChooser(cfg.llm_model || "");
    // API keys are intentionally masked by the backend; leave those fields blank.
  } catch (err) {
    // backend not reachable, refreshStatus() already reports this
  }
}

document.getElementById("save").addEventListener("click", async () => {
  const update = {
    supermemory_url: document.getElementById("supermemory_url").value.trim(),
    llm_base_url: baseUrlEl.value.trim(),
    llm_model: resolveModel(),
    provider: providerEl.value,
  };
  const apiKey = document.getElementById("llm_api_key").value.trim();
  if (apiKey) update.llm_api_key = apiKey;
  const smKey = document.getElementById("supermemory_api_key").value.trim();
  if (smKey) update.supermemory_api_key = smKey;

  try {
    await BuddyBackend.setConfig(update);
    await refreshStatus();
  } catch (err) {
    statusEl.className = "bad";
    statusEl.textContent = `Could not save: ${err.message}`;
  }
});

refreshStatus();
loadConfig();
