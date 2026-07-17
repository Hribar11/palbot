from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shlex
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import discord
import psutil
from discord import app_commands
from dotenv import load_dotenv


load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("palbot")

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
GUILD_ID = int(os.environ["DISCORD_GUILD_ID"]) if os.getenv("DISCORD_GUILD_ID") else None
ALLOWED_ROLE = os.getenv("ALLOWED_ROLE_NAME", "Palworld Admin").strip()
SERVER_EXE = Path(os.getenv("PALSERVER_EXE", "")).expanduser().resolve()
WORKING_DIR = Path(os.getenv("PALSERVER_WORKING_DIR", str(SERVER_EXE.parent))).expanduser().resolve()
SERVER_ARGS = shlex.split(os.getenv("PALSERVER_ARGS", ""), posix=False)
STOP_TIMEOUT = max(1, int(os.getenv("STOP_TIMEOUT_SECONDS", "30")))
REST_API_URL = os.getenv("PAL_REST_API_URL", "http://127.0.0.1:8212/v1/api").rstrip("/")
REST_API_USER = os.getenv("PAL_REST_API_USER", "admin")
REST_API_PASSWORD = os.getenv("PAL_REST_API_PASSWORD", "")
SHUTDOWN_DELAY = max(0, int(os.getenv("SHUTDOWN_DELAY_SECONDS", "10")))
SHUTDOWN_MESSAGE = os.getenv(
    "SHUTDOWN_MESSAGE", "Server is shutting down for maintenance."
)
STATE_FILE = Path(__file__).with_name("palbot-state.json")


def configured() -> None:
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing")
    if not str(SERVER_EXE) or not SERVER_EXE.is_file():
        raise RuntimeError(f"PALSERVER_EXE is not a file: {SERVER_EXE}")
    if not WORKING_DIR.is_dir():
        raise RuntimeError(f"PALSERVER_WORKING_DIR is not a directory: {WORKING_DIR}")


def executable_matches(process: psutil.Process) -> bool:
    try:
        return Path(process.exe()).resolve() == SERVER_EXE
    except (psutil.Error, OSError):
        return False


def read_tracked_process() -> psutil.Process | None:
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        process = psutil.Process(int(state["pid"]))
        if process.create_time() == state["create_time"] and executable_matches(process):
            return process
    except (FileNotFoundError, KeyError, ValueError, json.JSONDecodeError, psutil.Error):
        pass
    return None


def find_server_process() -> psutil.Process | None:
    tracked = read_tracked_process()
    if tracked:
        return tracked
    for process in psutil.process_iter(["pid"]):
        if executable_matches(process):
            return process
    return None


def start_server_sync() -> tuple[bool, str]:
    existing = find_server_process()
    if existing:
        return False, f"The Palworld server is already running (PID {existing.pid})."

    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    process = subprocess.Popen(
        [str(SERVER_EXE), *SERVER_ARGS],
        cwd=WORKING_DIR,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
        close_fds=True,
    )
    tracked = psutil.Process(process.pid)
    STATE_FILE.write_text(
        json.dumps({"pid": process.pid, "create_time": tracked.create_time()}),
        encoding="utf-8",
    )
    return True, f"Palworld server started (PID {process.pid})."


def pal_api_post(endpoint: str, payload: dict | None = None) -> None:
    if not REST_API_PASSWORD:
        raise RuntimeError("PAL_REST_API_PASSWORD is missing")

    credentials = base64.b64encode(
        f"{REST_API_USER}:{REST_API_PASSWORD}".encode("utf-8")
    ).decode("ascii")
    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    request = urllib.request.Request(
        f"{REST_API_URL}/{endpoint.lstrip('/')}",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError(f"Palworld API returned HTTP {response.status}")
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise RuntimeError("Palworld REST API rejected the username or password") from error
        raise RuntimeError(f"Palworld REST API returned HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not connect to the Palworld REST API: {error.reason}") from error


def force_stop_process_tree(process: psutil.Process) -> None:
    children = process.children(recursive=True)
    targets = children + [process]
    for target in reversed(targets):
        try:
            target.terminate()
        except psutil.Error:
            pass

    _, alive = psutil.wait_procs(targets, timeout=STOP_TIMEOUT)
    for target in alive:
        try:
            target.kill()
        except psutil.Error:
            pass
    psutil.wait_procs(alive, timeout=5)


def stop_server_sync() -> tuple[bool, str]:
    process = find_server_process()
    if not process:
        return False, "The Palworld server is not running."

    pid = process.pid
    # Refuse to terminate the process if saving or authentication fails.
    pal_api_post("save")
    pal_api_post(
        "shutdown",
        {"waittime": SHUTDOWN_DELAY, "message": SHUTDOWN_MESSAGE},
    )

    try:
        process.wait(timeout=SHUTDOWN_DELAY + STOP_TIMEOUT)
        forced = False
    except psutil.TimeoutExpired:
        log.warning("Graceful Palworld shutdown timed out; terminating process tree")
        force_stop_process_tree(process)
        forced = True

    STATE_FILE.unlink(missing_ok=True)
    suffix = " (forced after graceful shutdown timed out)" if forced else ""
    return True, f"World saved and Palworld server stopped (PID {pid}){suffix}."


class PalBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.operation_lock = asyncio.Lock()

    async def setup_hook(self) -> None:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Commands synced to guild %s", GUILD_ID)
        else:
            await self.tree.sync()
            log.info("Global commands synced")


bot = PalBot()


def is_authorized(interaction: discord.Interaction) -> bool:
    member = interaction.user
    return isinstance(member, discord.Member) and any(role.name == ALLOWED_ROLE for role in member.roles)


async def require_authorized(interaction: discord.Interaction) -> bool:
    if is_authorized(interaction):
        return True
    await interaction.response.send_message(
        f"You need the `{ALLOWED_ROLE}` role to use this command.", ephemeral=True
    )
    return False


@bot.tree.command(name="palstart", description="Start the Palworld dedicated server")
async def palstart(interaction: discord.Interaction) -> None:
    if not await require_authorized(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    async with bot.operation_lock:
        try:
            _, message = await asyncio.to_thread(start_server_sync)
        except Exception:
            log.exception("Could not start server")
            message = "Starting the server failed. Check the bot log on the Windows server."
    await interaction.followup.send(message, ephemeral=True)


@bot.tree.command(name="palstop", description="Stop the Palworld dedicated server")
async def palstop(interaction: discord.Interaction) -> None:
    if not await require_authorized(interaction):
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    async with bot.operation_lock:
        try:
            _, message = await asyncio.to_thread(stop_server_sync)
        except Exception as error:
            log.exception("Could not stop server")
            message = f"Stopping failed safely; the server was left running: {error}"
    await interaction.followup.send(message, ephemeral=True)


@bot.tree.command(name="palstatus", description="Show whether the Palworld server is running")
async def palstatus(interaction: discord.Interaction) -> None:
    if not await require_authorized(interaction):
        return
    process = await asyncio.to_thread(find_server_process)
    message = f"Palworld server is running (PID {process.pid})." if process else "Palworld server is stopped."
    await interaction.response.send_message(message, ephemeral=True)


@bot.event
async def on_ready() -> None:
    log.info("Signed in as %s (%s)", bot.user, bot.user.id if bot.user else "unknown")


if __name__ == "__main__":
    configured()
    bot.run(TOKEN, log_handler=None)
