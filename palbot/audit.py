from __future__ import annotations

import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Any

import discord
from discord import app_commands

from palbot.settings import COMMAND_LOG_BACKUPS, COMMAND_LOG_FILE, COMMAND_LOG_MAX_BYTES


def _configure_audit_logger() -> logging.Logger:
    logger = logging.getLogger("palbot.audit")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        COMMAND_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            COMMAND_LOG_FILE,
            maxBytes=COMMAND_LOG_MAX_BYTES,
            backupCount=COMMAND_LOG_BACKUPS,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    return logger


audit_log = _configure_audit_logger()


def flatten_command_options(options: list[dict[str, Any]]) -> dict[str, Any]:
    """Flatten Discord's nested subcommand options into safe JSON fields."""
    flattened: dict[str, Any] = {}
    for option in options:
        nested = option.get("options")
        if isinstance(nested, list):
            flattened.update(flatten_command_options(nested))
        elif "value" in option:
            flattened[str(option.get("name", "unknown"))] = option["value"]
    return flattened


def write_command_audit(interaction: discord.Interaction) -> None:
    data = interaction.data if isinstance(interaction.data, dict) else {}
    options = data.get("options", [])
    command = interaction.command
    record = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "event": "command_invoked",
        "command": command.qualified_name if command else data.get("name", "unknown"),
        "parameters": flatten_command_options(options) if isinstance(options, list) else {},
        "user": str(interaction.user),
        "user_id": interaction.user.id,
        "guild_id": interaction.guild_id,
        "channel_id": interaction.channel_id,
    }
    audit_log.info(json.dumps(record, ensure_ascii=False, separators=(",", ":")))


class AuditCommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        write_command_audit(interaction)
        return True

