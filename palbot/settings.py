from __future__ import annotations

import os
import shlex
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
GUILD_ID = int(os.environ["DISCORD_GUILD_ID"]) if os.getenv("DISCORD_GUILD_ID") else None
PLAYER_ROLE = os.getenv(
    "PALWORLD_PLAYER_ROLE_NAME",
    os.getenv("ALLOWED_ROLE_NAME", "Palworld Players"),
).strip()
ADMIN_ROLE = os.getenv("PALWORLD_ADMIN_ROLE_NAME", "Palworld Admins").strip()

SERVER_EXE = Path(os.getenv("PALSERVER_EXE", "")).expanduser().resolve()
WORKING_DIR = Path(
    os.getenv("PALSERVER_WORKING_DIR", str(SERVER_EXE.parent))
).expanduser().resolve()
SERVER_ARGS = shlex.split(os.getenv("PALSERVER_ARGS", ""), posix=False)
SETTINGS_INI = Path(
    os.getenv(
        "PALWORLD_SETTINGS_INI",
        str(
            WORKING_DIR
            / "Pal"
            / "Saved"
            / "Config"
            / "WindowsServer"
            / "PalWorldSettings.ini"
        ),
    )
).expanduser().resolve()

STOP_TIMEOUT = max(1, int(os.getenv("STOP_TIMEOUT_SECONDS", "30")))
REST_API_URL = os.getenv(
    "PAL_REST_API_URL", "http://127.0.0.1:8212/v1/api"
).rstrip("/")
REST_API_USER = os.getenv("PAL_REST_API_USER", "admin")
REST_API_PASSWORD = os.getenv("PAL_REST_API_PASSWORD", "")
SHUTDOWN_DELAY = max(0, int(os.getenv("SHUTDOWN_DELAY_SECONDS", "10")))
SHUTDOWN_MESSAGE = os.getenv(
    "SHUTDOWN_MESSAGE", "Server is shutting down for maintenance."
)
STATE_FILE = Path(__file__).parent.parent / "palbot-state.json"
COMMAND_LOG_FILE = Path(
    os.getenv(
        "COMMAND_LOG_FILE",
        str(Path(__file__).parent.parent / "logs" / "commands.log"),
    )
).expanduser().resolve()
COMMAND_LOG_MAX_BYTES = max(1024, int(os.getenv("COMMAND_LOG_MAX_BYTES", "5242880")))
COMMAND_LOG_BACKUPS = max(1, int(os.getenv("COMMAND_LOG_BACKUPS", "5")))


def validate_startup_config() -> None:
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing")
    if not SERVER_EXE.is_file():
        raise RuntimeError(f"PALSERVER_EXE is not a file: {SERVER_EXE}")
    if not WORKING_DIR.is_dir():
        raise RuntimeError(f"PALSERVER_WORKING_DIR is not a directory: {WORKING_DIR}")
