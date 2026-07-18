from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord

from palbot.permissions import require_player
from palbot.server import find_server_process, format_duration, get_server_stats_sync

if TYPE_CHECKING:
    from palbot.client import PalBot


log = logging.getLogger("palbot.commands.stats")


def register(bot: "PalBot") -> None:
    @bot.tree.command(name="palstats", description="Show live Palworld server statistics")
    async def palstats(interaction: discord.Interaction) -> None:
        if not await require_player(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        if not await asyncio.to_thread(find_server_process):
            await interaction.followup.send("Palworld server is stopped.", ephemeral=True)
            return
        try:
            stats = await asyncio.to_thread(get_server_stats_sync)
            embed = discord.Embed(
                title="Palworld Server Stats", color=discord.Color.green()
            )
            embed.add_field(
                name="Players",
                value=f"{stats.get('currentplayernum', '?')} / {stats.get('maxplayernum', '?')}",
            )
            embed.add_field(name="Server FPS", value=str(stats.get("serverfps", "?")))
            frame_time = stats.get("serverframetime")
            embed.add_field(
                name="Frame time",
                value=(
                    f"{frame_time:.2f} ms"
                    if isinstance(frame_time, (int, float))
                    else "?"
                ),
            )
            embed.add_field(
                name="Uptime", value=format_duration(int(stats.get("uptime", 0)))
            )
            embed.add_field(name="World days", value=str(stats.get("days", "?")))
            embed.add_field(name="Base camps", value=str(stats.get("basecampnum", "?")))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as error:
            log.exception("Could not read server statistics")
            await interaction.followup.send(
                f"Could not read Palworld server statistics: {error}", ephemeral=True
            )
