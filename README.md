# Buddy

Right-click any text or link to save it into your own local memory store, then chat with everything you've saved.

Fully local: your saved content, your supermemory instance, your own LLM API key. Nothing routes through a server anyone else runs.

## Setup

Buddy has two separate local pieces: **supermemory itself** (the memory store, a separate program you install once) and **the Buddy backend** (this repo's Python server, which talks to supermemory and your LLM on the extension's behalf). They're installed independently.

1. Install supermemory (one time, outside this repo — Buddy can detect it but can't install or start it for you):

   **macOS / Linux:**

   ```bash
   curl -fsSL https://supermemory.ai/install | bash
   # or, on any OS with Node.js:  npx supermemory local
   ```

   **Windows** (no `curl | bash` — use Node.js):

   ```powershell
   npx supermemory local
   ```

   Then run it **in this terminal, interactively** — first boot needs a real terminal (TTY) to walk you through picking a model provider (OpenAI/Anthropic/Gemini/Groq/Ollama) and pasting that provider's API key:

   ```bash
   supermemory-server
   ```

   > **Where your memories are stored:** supermemory keeps its data in a `.supermemory` folder relative to **whatever directory you launch it from** — so starting it from different folders gives you separate, empty stores. To pin one stable location, launch it with an explicit data dir:
   >
   > - macOS / Linux: `SUPERMEMORY_DATA_DIR="$HOME/.supermemory-data" supermemory-server`
   > - Windows (PowerShell): `$env:SUPERMEMORY_DATA_DIR="$HOME\.supermemory-data"; supermemory-server`

   Once it's up, it prints a client key starting with `sm_...` — that's what Buddy uses to authenticate to it (separate from the model-provider key you just entered). Leave this running in its own terminal.

2. Install and start the Buddy backend, in a second terminal:

   **macOS / Linux:**

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   buddy start
   ```

   **Windows (PowerShell):**

   ```powershell
   cd backend
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -e .
   buddy start
   ```

   (On Linux distros with PEP 668 "externally managed" Python — Arch, Debian 12+, etc. — a bare `pip install -e .` refuses to run outside a venv, so the venv above isn't optional there. Either way, `buddy` is only on `PATH` while the venv is activated — otherwise call it by full path, e.g. `.venv/bin/buddy start` or `.venv\Scripts\buddy.exe start`.)

   `buddy start` checks supermemory's state and tells you exactly what's missing if anything is: not installed, installed-but-not-running, or running-but-no-key-configured. It never tries to launch supermemory itself — that step has to be interactive (see step 1).

3. Load the extension:
   - Open `chrome://extensions`
   - Enable **Developer mode** (top right)
   - Click **Load unpacked**, select the `extension/` folder in this repo

4. Configure keys — open the extension's **Options** page (right-click the icon → Options, or from `chrome://extensions`), and fill in:
   - the `sm_...` key supermemory printed in step 1
   - your LLM base URL, API key, and model (any OpenAI-compatible provider — Groq, OpenAI, a local Ollama endpoint, etc.) — this is for Buddy's own chat feature, separate from the model provider key supermemory itself uses internally

5. Try it:
   - Select some text on any page, right-click → **Add to Buddy** (or **Add to Buddy with comment** to attach a note).
   - Right-click a link → same options — the backend fetches and extracts the article content automatically.
   - Click the extension icon to open the side panel and chat about what you've saved.
