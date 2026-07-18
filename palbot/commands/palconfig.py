from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord
from discord import app_commands

from palbot.ini_editor import (
    CONFIG_PARAMETERS,
    get_config_value_sync,
    set_config_value_sync,
)
from palbot.permissions import require_admin

if TYPE_CHECKING:
    from palbot.client import PalBot


log = logging.getLogger("palbot.commands.palconfig")


async def parameter_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    del interaction
    search = current.lower()
    matches = []
    for parameter, (label, *_rest) in CONFIG_PARAMETERS.items():
        if search in parameter.lower() or search in label.lower():
            matches.append(
                app_commands.Choice(name=f"{label} ({parameter})", value=parameter)
            )
    return matches[:25]


async def value_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    parameter = getattr(interaction.namespace, "parameter", None)
    spec = CONFIG_PARAMETERS.get(parameter)
    if not spec:
        return []
    _, kind, minimum, maximum, choices = spec
    if kind == "bool":
        suggestions = ("True", "False")
    elif kind == "choice":
        suggestions = choices
    elif kind in {"int", "float"}:
        suggestions = (str(minimum), str(maximum))
    else:
        return []
    return [
        app_commands.Choice(name=value, value=value)
        for value in suggestions
        if current.lower() in value.lower()
    ][:25]


def register(bot: "PalBot") -> None:
    group = app_commands.Group(
        name="palconfig", description="View or edit Palworld server settings"
    )

    @group.command(name="get", description="Read one Palworld setting")
    @app_commands.describe(parameter="Setting to read; start typing to search")
    @app_commands.autocomplete(parameter=parameter_autocomplete)
    async def palconfig_get(
        interaction: discord.Interaction, parameter: str
    ) -> None:
        if not await require_admin(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            value = await asyncio.to_thread(get_config_value_sync, parameter)
            label = CONFIG_PARAMETERS[parameter][0]
            await interaction.followup.send(
                f"**{label}** (`{parameter}`) = `{value}`", ephemeral=True
            )
        except Exception as error:
            log.exception("Could not read Palworld setting")
            await interaction.followup.send(
                f"Could not read setting: {error}", ephemeral=True
            )

    @group.command(name="set", description="Change a setting while Palworld is stopped")
    @app_commands.describe(
        parameter="Setting to change; start typing to search",
        value="New value; booleans and choices autocomplete",
    )
    @app_commands.autocomplete(
        parameter=parameter_autocomplete, value=value_autocomplete
    )
    async def palconfig_set(
        interaction: discord.Interaction, parameter: str, value: str
    ) -> None:
        if not await require_admin(interaction):
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        async with bot.operation_lock:
            try:
                old_value, new_value, backup_path = await asyncio.to_thread(
                    set_config_value_sync, parameter, value
                )
                label = CONFIG_PARAMETERS[parameter][0]
                log.info(
                    "%s changed %s from %s to %s",
                    interaction.user,
                    parameter,
                    old_value,
                    new_value,
                )
                await interaction.followup.send(
                    f"Updated **{label}** (`{parameter}`): `{old_value}` → `{new_value}`\n"
                    f"Backup: `{backup_path.name}`. Start Palworld to apply the change.",
                    ephemeral=True,
                )
            except Exception as error:
                log.exception("Could not update Palworld setting")
                await interaction.followup.send(
                    f"Configuration was not changed: {error}", ephemeral=True
                )

    @group.command(name="list", description="List settings PalBot is allowed to edit")
    async def palconfig_list(interaction: discord.Interaction) -> None:
        if not await require_admin(interaction):
            return
        lines = []
        for parameter, (label, kind, minimum, maximum, choices) in CONFIG_PARAMETERS.items():
            if choices:
                constraint = " | ".join(choices)
            elif minimum is not None:
                constraint = f"{kind}, {minimum}–{maximum}"
            else:
                constraint = kind
            lines.append(f"`{parameter}` — {label} ({constraint})")
        embed = discord.Embed(
            title="Editable Palworld Settings",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="The server must be stopped before using /palconfig set.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    bot.tree.add_command(group)
