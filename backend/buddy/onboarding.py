"""Interactive terminal onboarding, run by `buddy start`.

Collects the four things Buddy needs and persists them to the env file
at ~/.buddy/.env (plain KEY=value lines — see config.py):
  - provider        (groq / openai / anthropic / gemini / ollama)
  - llm_api_key     (the provider key, e.g. a Groq gsk_... key)
  - llm_model       (model name for that provider)
  - supermemory_api_key  (the sm_... key supermemory prints — the prompt
                          hints the user to run `npx supermemory local`
                          in another terminal to get it)

Anything already present in ~/.buddy/.env is kept and not re-asked, so
onboarding only prompts for what's missing. A user who'd rather not be
prompted can just fill those KEYs into ~/.buddy/.env by hand.

Presentation uses `rich` for a styled step-by-step wizard (colored
bullet + dim explanation, masked key entry, green ✓ confirmation),
loosely matching supermemory's own onboarding look.
"""

import sys

from rich.console import Console
from rich.prompt import Prompt

from .config import CONFIG_PATH, PROVIDER_BASE_URLS, load_config, save_config

console = Console()


def _masked_input(prompt: str = "  ") -> str:
    """Read a line while echoing a dot per character (like a password field
    that shows ••••). Falls back to plain input when there's no real TTY.
    Cross-platform: termios on Unix, msvcrt on Windows."""
    if not sys.stdin.isatty():
        return input(prompt).strip()

    sys.stdout.write(prompt)
    sys.stdout.flush()

    try:
        if sys.platform == "win32":
            import msvcrt

            chars: list[str] = []
            while True:
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    break
                if ch == "\003":  # Ctrl-C
                    raise KeyboardInterrupt
                if ch == "\b":  # backspace
                    if chars:
                        chars.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                    continue
                chars.append(ch)
                sys.stdout.write("•")
                sys.stdout.flush()
            sys.stdout.write("\n")
            return "".join(chars).strip()

        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        chars = []
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n"):
                    break
                if ch == "\003":  # Ctrl-C
                    raise KeyboardInterrupt
                if ch in ("\x7f", "\b"):  # backspace / delete
                    if chars:
                        chars.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                    continue
                chars.append(ch)
                sys.stdout.write("•")
                sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\n")
        return "".join(chars).strip()
    except (EOFError, KeyboardInterrupt):
        sys.stdout.write("\n")
        return ""


def _step(explanation: str) -> None:
    """A blue bullet + dim explanation line, like the screenshot's steps."""
    console.print()
    console.print(f"[bold blue]●[/] {explanation}")


def _ask(label: str, secret: bool = False, choices: list[str] | None = None) -> str:
    """A dim '◇ label' prompt line. Secrets echo dots (••••) as you type."""
    console.print(f"[dim]◇ {label}[/]")
    if secret:
        return _masked_input("  ")
    try:
        return Prompt.ask("  ", choices=choices, show_choices=False, default="").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def _saved(what: str) -> None:
    console.print(f"[bold green]✓[/] {what}")


def needs_onboarding(cfg: dict) -> bool:
    required = ["provider", "llm_api_key", "llm_model", "supermemory_api_key"]
    return any(not cfg.get(f) for f in required)


def run_onboarding() -> dict:
    cfg = load_config()
    updates: dict = {}

    def resolve(field: str) -> str:
        return cfg.get(field, "")

    console.print()
    console.rule("[bold]Buddy setup")
    console.print(
        f"[dim]I'll ask only for what isn't already in {CONFIG_PATH}. "
        "You can also fill that file in by hand instead.[/]"
    )

    # 1. provider
    provider = resolve("provider")
    if not provider:
        _step("Which LLM provider do you want to use? (for chat)")
        provider = _ask(
            f"provider  ({' / '.join(PROVIDER_BASE_URLS)})",
            choices=list(PROVIDER_BASE_URLS),
        ).lower()
        if provider:
            updates["provider"] = provider
            if provider in PROVIDER_BASE_URLS:
                updates["llm_base_url"] = PROVIDER_BASE_URLS[provider]
            _saved(f"provider set to {provider}")
    provider = provider or cfg.get("provider", "")

    # 2. provider API key (e.g. Groq key)
    if not resolve("llm_api_key"):
        _step(f"Paste your {provider or 'provider'} API key. It's saved to {CONFIG_PATH}.")
        key = _ask(f"{(provider or 'PROVIDER').upper()}_API_KEY", secret=True)
        if key:
            updates["llm_api_key"] = key
            _saved(f"saved {(provider or 'provider').upper()} API key")

    # 3. model name
    if not resolve("llm_model"):
        _step("Which model? (e.g. llama-3.3-70b-versatile for Groq)")
        model = _ask("model")
        if model:
            updates["llm_model"] = model
            _saved(f"model set to {model}")

    # 4. supermemory key — with the hint to go get it via npx
    if not resolve("supermemory_api_key"):
        _step(
            "Supermemory key. In a [bold]separate terminal[/] run "
            "[bold cyan]npx supermemory local[/], follow its prompts, and it prints a "
            "key starting with [bold]sm_[/]. Leave it running, then paste the key here."
        )
        sm_key = _ask("SUPERMEMORY_API_KEY (sm_...)", secret=True)
        if sm_key:
            updates["supermemory_api_key"] = sm_key
            _saved("saved supermemory key")

    if updates:
        save_config(updates)
        console.print()
        console.print(f"[bold green]✓[/] All set — written to [bold]{CONFIG_PATH}[/]")

    return load_config()
