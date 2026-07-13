"""Detect the local supermemory install/run state and tell the user what
to do next, in an OS-agnostic way (macOS / Windows / Linux).

Buddy deliberately never tries to launch `supermemory-server` itself:
per supermemory's self-hosting docs, first boot runs an *interactive*
setup wizard (pick a model provider, paste its key) that only triggers
with a real TTY — "there is no wizard without a TTY." A background
subprocess has no TTY, so spawning it just fatal-exits with "No model
provider API key configured." Running it in the user's own terminal is
the only path that works for first boot.

Real install (from https://supermemory.ai/docs/self-hosting/overview):
  - curl -fsSL https://supermemory.ai/install | bash   (macOS / Linux)
  - npx supermemory local                              (any OS with Node)
`pip install supermemory` (a dependency of this backend) is the REST API
*client* SDK only — it never installs the server binary.
"""

import os
import platform
import shutil
from pathlib import Path
from typing import Literal

from .supermemory_client import SupermemoryClient

State = Literal["ready", "not_installed", "installed_not_running", "running_needs_key"]

INSTALL_CMD_SHELL = "curl -fsSL https://supermemory.ai/install | bash"
INSTALL_CMD_NPX = "npx supermemory local"


def _binary_names() -> list[str]:
    # Windows: the curl installer isn't used; installs come via npm/npx, which
    # create .cmd/.exe shims. shutil.which() already honors PATHEXT, but the
    # explicit fallback scan needs the real filenames.
    if platform.system() == "Windows":
        return ["supermemory-server.exe", "supermemory-server.cmd", "supermemory-server"]
    return ["supermemory-server"]


def _candidate_dirs() -> list[Path]:
    home = Path.home()
    system = platform.system()
    dirs = [home / ".local" / "bin", home / ".supermemory" / "bin"]

    if system == "Darwin":
        dirs += [Path("/opt/homebrew/bin"), Path("/usr/local/bin")]  # Apple Silicon, Intel
    elif system == "Linux":
        dirs += [Path("/usr/local/bin")]
    elif system == "Windows":
        for env_var, sub in (("APPDATA", "npm"), ("LOCALAPPDATA", "supermemory\\bin")):
            base = os.environ.get(env_var)
            if base:
                dirs.append(Path(base) / sub)
    return dirs


def find_supermemory_binary() -> str | None:
    """Best-effort. NOTE: an `npx supermemory local` install may leave no
    persistent binary at all, so a None result does NOT prove "not running"
    — always check reachability first (see check_state)."""
    on_path = shutil.which("supermemory-server")
    if on_path:
        return on_path
    for directory in _candidate_dirs():
        for name in _binary_names():
            candidate = directory / name
            if candidate.exists():
                return str(candidate)
    return None


def install_commands() -> list[str]:
    if platform.system() == "Windows":
        return [INSTALL_CMD_NPX]  # no `curl | bash` on Windows
    return [INSTALL_CMD_SHELL, INSTALL_CMD_NPX]


def recommended_data_dir() -> Path:
    """A stable, absolute data dir so memories don't get tied to whatever
    folder the user happened to launch the server from (supermemory defaults
    SUPERMEMORY_DATA_DIR to ./.supermemory, i.e. relative to CWD)."""
    return Path.home() / ".supermemory-data"


def _set_data_dir_hint() -> str:
    data_dir = recommended_data_dir()
    if platform.system() == "Windows":
        # PowerShell syntax
        return f'$env:SUPERMEMORY_DATA_DIR="{data_dir}"; supermemory-server'
    return f'SUPERMEMORY_DATA_DIR="{data_dir}" supermemory-server'


async def check_state(base_url: str, api_key: str) -> State:
    """Reachability-first: a running server (even one launched ephemerally via
    npx, with no binary on PATH) must win over binary detection."""
    client = SupermemoryClient(base_url, api_key)

    if await client.server_reachable():
        if api_key and await client.authenticated():
            return "ready"
        return "running_needs_key"

    # Not reachable — is it at least installed?
    if find_supermemory_binary() is None:
        return "not_installed"
    return "installed_not_running"


def guidance_for(state: State, base_url: str) -> str:
    if state == "not_installed":
        cmds = "\n".join(f"    {c}" for c in install_commands())
        return (
            "Buddy: supermemory isn't installed (or isn't on your PATH). "
            "Install it yourself in a terminal:\n"
            f"{cmds}\n"
            "  then re-run `buddy start`."
        )
    if state == "installed_not_running":
        return (
            "Buddy: supermemory is installed but not running. Start it yourself in a "
            "terminal (Buddy can't — first boot needs an interactive wizard with a real "
            "terminal to pick a model provider and paste its API key):\n"
            "    supermemory-server\n"
            "  (or `npx supermemory local` if that's how you installed it)\n"
            "  TIP: its memory store defaults to a `.supermemory` folder in whatever "
            "directory you launch from — so launching from different folders gives you "
            "different, separate stores. To pin one stable location, start it like:\n"
            f"    {_set_data_dir_hint()}\n"
            "  Once it's up it prints a client key starting with 'sm_' — re-run "
            "`buddy start` and Buddy will tell you where to put it."
        )
    if state == "running_needs_key":
        return (
            f"Buddy: supermemory is running at {base_url} but Buddy has no working API key "
            "for it yet. Copy the 'sm_...' key it printed on boot (in the terminal you ran "
            "`supermemory-server` in) and paste it into Buddy's extension options page, "
            "in the 'Supermemory API key' field, then Save."
        )
    return "Buddy: supermemory is up and authenticated."
