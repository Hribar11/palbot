from __future__ import annotations

import base64
import json
import logging
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import psutil

from palbot.settings import (
    REST_API_PASSWORD,
    REST_API_URL,
    REST_API_USER,
    SERVER_ARGS,
    SERVER_EXE,
    SHUTDOWN_DELAY,
    SHUTDOWN_MESSAGE,
    STATE_FILE,
    STOP_TIMEOUT,
    WORKING_DIR,
)


log = logging.getLogger("palbot.server")


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

    process = subprocess.Popen(
        [str(SERVER_EXE), *SERVER_ARGS],
        cwd=WORKING_DIR,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )
    tracked = psutil.Process(process.pid)
    STATE_FILE.write_text(
        json.dumps({"pid": process.pid, "create_time": tracked.create_time()}),
        encoding="utf-8",
    )
    return True, f"Palworld server started (PID {process.pid})."


def pal_api_request(
    endpoint: str, method: str = "GET", payload: dict | None = None
) -> dict:
    if not REST_API_PASSWORD:
        raise RuntimeError("PAL_REST_API_PASSWORD is missing")
    credentials = base64.b64encode(
        f"{REST_API_USER}:{REST_API_PASSWORD}".encode("utf-8")
    ).decode("ascii")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{REST_API_URL}/{endpoint.lstrip('/')}",
        data=body,
        method=method,
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
            response_body = response.read()
            return json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as error:
        if error.code == 401:
            raise RuntimeError(
                "Palworld REST API rejected the username or password"
            ) from error
        raise RuntimeError(f"Palworld REST API returned HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Could not connect to the Palworld REST API: {error.reason}"
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Palworld REST API returned invalid JSON") from error


def get_server_stats_sync() -> dict:
    return pal_api_request("metrics")


def force_stop_process_tree(process: psutil.Process) -> None:
    targets = process.children(recursive=True) + [process]
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
    pal_api_request("save", method="POST")
    pal_api_request(
        "shutdown",
        method="POST",
        payload={"waittime": SHUTDOWN_DELAY, "message": SHUTDOWN_MESSAGE},
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


def format_duration(total_seconds: int) -> str:
    days, remainder = divmod(max(0, total_seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)
