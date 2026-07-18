from __future__ import annotations

from typing import TYPE_CHECKING

from palbot.commands import help, palconfig, start, stats, status, stop

if TYPE_CHECKING:
    from palbot.client import PalBot


def register_commands(bot: "PalBot") -> None:
    start.register(bot)
    stop.register(bot)
    status.register(bot)
    stats.register(bot)
    palconfig.register(bot)
    help.register(bot)

