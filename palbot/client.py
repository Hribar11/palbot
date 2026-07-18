from __future__ import annotations

import asyncio
import logging

import discord
from discord import app_commands

from palbot.commands import register_commands
from palbot.settings import GUILD_ID


log = logging.getLogger("palbot.client")


class PalBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.operation_lock = asyncio.Lock()
        register_commands(self)

    async def setup_hook(self) -> None:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Commands synced to guild %s", GUILD_ID)
        else:
            await self.tree.sync()
            log.info("Global commands synced")

    async def on_ready(self) -> None:
        log.info("Signed in as %s (%s)", self.user, self.user.id if self.user else "unknown")

