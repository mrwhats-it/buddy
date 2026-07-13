"""Config lives in a single human-editable env file: ~/.buddy/.env

Format is plain `KEY=value` lines (the same thing a user could type or
`export`), so anyone can open it in a text editor and fill/change keys
without going through onboarding. Buddy reads it on startup.

Internally we use lowercase field names (e.g. `llm_api_key`); on disk
they're written UPPERCASE as env-style vars (e.g. `LLM_API_KEY`).
"""

from pathlib import Path

CONFIG_DIR = Path.home() / ".buddy"
ENV_PATH = CONFIG_DIR / ".env"
# Back-compat / discoverability: keep the old name pointing at the env file
# so other modules that print "where config lives" stay correct.
CONFIG_PATH = ENV_PATH

DEFAULTS = {
    "supermemory_url": "http://localhost:6767",
    "supermemory_api_key": "",
    "provider": "",
    "llm_base_url": "",
    "llm_api_key": "",
    "llm_model": "",
}

# Known OpenAI-compatible providers → their chat base URL. Used so onboarding
# only has to ask for a provider name + key, not a raw base URL.
PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "ollama": "http://localhost:11434/v1",
}


def _field_to_env(field: str) -> str:
    return field.upper()


def _parse_env_file(text: str) -> dict:
    parsed: dict = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        parsed[key.strip().lower()] = value.strip().strip('"').strip("'")
    return parsed


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if ENV_PATH.exists():
        on_disk = _parse_env_file(ENV_PATH.read_text())
        for field in DEFAULTS:
            if on_disk.get(field):
                cfg[field] = on_disk[field]
    return cfg


def save_config(updates: dict) -> dict:
    current = load_config()
    current.update({k: v for k, v in updates.items() if v is not None})

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Buddy config — plain KEY=value env file. Edit by hand or via `buddy start`.",
        "",
    ]
    for field in DEFAULTS:
        lines.append(f"{_field_to_env(field)}={current.get(field, '')}")
    ENV_PATH.write_text("\n".join(lines) + "\n")
    return current
