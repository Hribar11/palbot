from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord

from palbot.permissions import require_player
from palbot.server import find_server_process

if TYPE_CHECKING:
    from palbot.client import PalBot


def register(bot: "PalBot") -> None:
    @bot.tree.command(name="palstatus", description="Show whether Palworld is running")
    async def palstatus(interaction: discord.Interaction) -> None:
        if not await require_player(interaction):
            return
        process = await asyncio.to_thread(find_server_process)
        message = (
            f"Palworld server is running (PID {process.pid})."
            if process
            else "Palworld server is stopped."
        )
        await interaction.response.send_message(message, ephemeral=True)

