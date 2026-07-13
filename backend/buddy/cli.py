import asyncio
from pathlib import Path

import uvicorn

from .config import CONFIG_PATH, load_config
from .onboarding import needs_onboarding, run_onboarding
from .supermemory_installer import check_state, guidance_for

EXTENSION_DIR = Path(__file__).resolve().parent.parent.parent / "extension"


def main():
    cfg = load_config()

    # Interactive onboarding: collect provider / key / model / supermem key
    # if any are missing. Runs in the terminal, so it has a TTY to prompt with.
    if needs_onboarding(cfg):
        cfg = run_onboarding()

    print("Buddy: checking supermemory...")
    state = asyncio.run(check_state(cfg["supermemory_url"], cfg["supermemory_api_key"]))
    print(guidance_for(state, cfg["supermemory_url"]))
    if state != "ready":
        print(f"Buddy: config lives at {CONFIG_PATH} if you want to inspect/edit it directly.")

    if not (cfg["llm_base_url"] and cfg["llm_api_key"] and cfg["llm_model"]):
        print(
            "Buddy: LLM (chat) isn't fully configured yet — re-run `buddy start` to finish "
            "onboarding, or set it from the extension's options page."
        )

    print(
        "\nBuddy: to load the extension, open chrome://extensions in Chrome, enable "
        "Developer mode, click 'Load unpacked', and select:\n"
        f"  {EXTENSION_DIR}\n"
    )

    print("Buddy: starting backend on http://localhost:8420 ...")
    uvicorn.run("buddy.server:app", host="127.0.0.1", port=8420, log_level="info")


if __name__ == "__main__":
    main()
