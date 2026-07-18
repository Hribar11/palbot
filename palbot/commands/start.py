from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord

from palbot.permissions import require_player
from palbot.server import start_server_sync

if TYPE_CHECKING:
    from palbot.client import PalBot


log = logging.getLogger("palbot.commands.start")


def register(bot: "PalBot") -> None:
    @bot.tree.command(name="palstart", description="Start the Palworld dedicated server")
    async def palstart(interaction: discord.Interaction) -> None:
        if not await require_player(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with bot.operation_lock:
            try:
                _, message = await asyncio.to_thread(start_server_sync)
            except Exception:
                log.exception("Could not start server")
                message = "Starting the server failed. Check the bot log on the Windows server."
        await interaction.followup.send(message, ephemeral=True)

