from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord

from palbot.permissions import require_player
from palbot.server import stop_server_sync

if TYPE_CHECKING:
    from palbot.client import PalBot


log = logging.getLogger("palbot.commands.stop")


def register(bot: "PalBot") -> None:
    @bot.tree.command(name="palstop", description="Stop the Palworld dedicated server")
    async def palstop(interaction: discord.Interaction) -> None:
        if not await require_player(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with bot.operation_lock:
            try:
                _, message = await asyncio.to_thread(stop_server_sync)
            except Exception as error:
                log.exception("Could not stop server")
                message = f"Stopping failed safely; the server was left running: {error}"
        await interaction.followup.send(message, ephemeral=True)

