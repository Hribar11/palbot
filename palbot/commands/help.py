from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from palbot.settings import ADMIN_ROLE, PLAYER_ROLE

if TYPE_CHECKING:
    from palbot.client import PalBot


def register(bot: "PalBot") -> None:
    @bot.tree.command(name="palhelp", description="List PalBot commands")
    async def palhelp(interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="PalBot Commands",
            description=(
                f"Server controls require `{PLAYER_ROLE}` or `{ADMIN_ROLE}`. "
                f"Configuration commands require `{ADMIN_ROLE}`."
            ),
            color=discord.Color.blurple(),
        )
        embed.add_field(name="/palstart", value="Start the Palworld server.", inline=False)
        embed.add_field(
            name="/palstop",
            value="Save the world and gracefully stop the server.",
            inline=False,
        )
        embed.add_field(
            name="/palstatus", value="Check whether the server is running.", inline=False
        )
        embed.add_field(
            name="/palstats",
            value="Show live server performance and world stats.",
            inline=False,
        )
        embed.add_field(
            name="/palconfig get|set|list",
            value="View or edit supported server settings (admins only).",
            inline=False,
        )
        embed.add_field(name="/palhelp", value="Show this command list.", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

