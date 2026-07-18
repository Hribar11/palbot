from __future__ import annotations

import discord

from palbot.settings import ADMIN_ROLE, PLAYER_ROLE


def has_role(interaction: discord.Interaction, role_name: str) -> bool:
    member = interaction.user
    return isinstance(member, discord.Member) and any(
        role.name == role_name for role in member.roles
    )


async def require_player(interaction: discord.Interaction) -> bool:
    if has_role(interaction, PLAYER_ROLE) or has_role(interaction, ADMIN_ROLE):
        return True
    await interaction.response.send_message(
        f"You need the `{PLAYER_ROLE}` or `{ADMIN_ROLE}` role to use this command.",
        ephemeral=True,
    )
    return False


async def require_admin(interaction: discord.Interaction) -> bool:
    if has_role(interaction, ADMIN_ROLE):
        return True
    await interaction.response.send_message(
        f"You need the `{ADMIN_ROLE}` role to use this command.", ephemeral=True
    )
    return False

