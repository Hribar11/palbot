from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from palbot.server import find_server_process
from palbot.settings import SETTINGS_INI


CONFIG_PARAMETERS = {
    "ServerName": ("Server name", "string", None, None, None),
    "ServerDescription": ("Server description", "string", None, None, None),
    "ServerPlayerMaxNum": ("Maximum players", "int", 1, 128, None),
    "DayTimeSpeedRate": ("Day speed", "float", 0.1, 5.0, None),
    "NightTimeSpeedRate": ("Night speed", "float", 0.1, 5.0, None),
    "ExpRate": ("Experience rate", "float", 0.1, 20.0, None),
    "PalCaptureRate": ("Pal capture rate", "float", 0.1, 20.0, None),
    "PalSpawnNumRate": ("Pal spawn rate", "float", 0.1, 3.0, None),
    "PalDamageRateAttack": ("Pal attack damage", "float", 0.1, 20.0, None),
    "PalDamageRateDefense": ("Pal damage taken", "float", 0.1, 20.0, None),
    "PlayerDamageRateAttack": ("Player attack damage", "float", 0.1, 20.0, None),
    "PlayerDamageRateDefense": ("Player damage taken", "float", 0.1, 20.0, None),
    "PlayerStaminaDecreaceRate": ("Player stamina drain", "float", 0.1, 20.0, None),
    "PlayerStomachDecreaceRate": ("Player hunger drain", "float", 0.1, 20.0, None),
    "PalStaminaDecreaceRate": ("Pal stamina drain", "float", 0.1, 20.0, None),
    "PalStomachDecreaceRate": ("Pal hunger drain", "float", 0.1, 20.0, None),
    "CollectionDropRate": ("Gatherable item rate", "float", 0.1, 20.0, None),
    "EnemyDropItemRate": ("Enemy drop rate", "float", 0.1, 20.0, None),
    "BaseCampWorkerMaxNum": ("Workers per base", "int", 1, 50, None),
    "GuildPlayerMaxNum": ("Players per guild", "int", 1, 100, None),
    "SupplyDropSpan": ("Supply drop interval (minutes)", "int", 1, 10080, None),
    "bEnableInvaderEnemy": ("Raids enabled", "bool", None, None, None),
    "bIsPvP": ("PvP enabled", "bool", None, None, None),
    "DeathPenalty": (
        "Death penalty",
        "choice",
        None,
        None,
        ("None", "Item", "ItemAndEquipment", "All"),
    ),
}


def validate_config_value(parameter: str, raw_value: str) -> str:
    if parameter not in CONFIG_PARAMETERS:
        raise ValueError("Unsupported parameter. Select one from autocomplete.")
    _, kind, minimum, maximum, choices = CONFIG_PARAMETERS[parameter]
    value = raw_value.strip()
    if kind == "string":
        if not value or len(value) > 120:
            raise ValueError("Text values must contain 1 to 120 characters.")
        if any(character in value for character in ('"', "\r", "\n")):
            raise ValueError("Text values cannot contain quotes or line breaks.")
        return f'"{value}"'
    if kind == "bool":
        normalized = value.lower()
        if normalized in {"true", "yes", "on", "1"}:
            return "True"
        if normalized in {"false", "no", "off", "0"}:
            return "False"
        raise ValueError("Use true or false.")
    if kind == "choice":
        match = next((choice for choice in choices if choice.lower() == value.lower()), None)
        if not match:
            raise ValueError(f"Allowed values: {', '.join(choices)}")
        return match
    try:
        number = int(value) if kind == "int" else float(value)
    except ValueError as error:
        raise ValueError(f"{parameter} requires a {kind} value.") from error
    if not minimum <= number <= maximum:
        raise ValueError(f"Value must be between {minimum} and {maximum}.")
    return str(number)


def read_option_settings() -> tuple[str, re.Match[str]]:
    if not SETTINGS_INI.is_file():
        raise RuntimeError(f"Settings file was not found: {SETTINGS_INI}")
    text = SETTINGS_INI.read_text(encoding="utf-8-sig")
    match = re.search(r"^OptionSettings=\((?P<settings>.*)\)\s*$", text, re.MULTILINE)
    if not match:
        raise RuntimeError("PalWorldSettings.ini has no valid OptionSettings=(...) line")
    return text, match


def config_value_pattern(parameter: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?P<prefix>(?:^|,)\s*{re.escape(parameter)}\s*=\s*)"
        rf'(?P<value>"(?:\\.|[^"\\])*"|[^,]*)'
    )


def get_config_value_sync(parameter: str) -> str:
    if parameter not in CONFIG_PARAMETERS:
        raise ValueError("Unsupported parameter. Select one from autocomplete.")
    _, option_match = read_option_settings()
    value_match = config_value_pattern(parameter).search(option_match.group("settings"))
    if not value_match:
        return "Not present (Palworld default applies)"
    value = value_match.group("value").strip()
    return value[1:-1] if value.startswith('"') and value.endswith('"') else value


def set_config_value_sync(parameter: str, raw_value: str) -> tuple[str, str, Path]:
    if find_server_process():
        raise RuntimeError("Stop the Palworld server before changing its configuration.")
    formatted_value = validate_config_value(parameter, raw_value)
    text, option_match = read_option_settings()
    settings = option_match.group("settings")
    value_pattern = config_value_pattern(parameter)
    existing = value_pattern.search(settings)
    old_value = existing.group("value").strip() if existing else "Not present (Palworld default)"
    if existing:
        new_settings = value_pattern.sub(
            lambda match: f"{match.group('prefix')}{formatted_value}", settings, count=1
        )
    else:
        separator = "," if settings.strip() else ""
        new_settings = f"{settings}{separator}{parameter}={formatted_value}"
    updated_text = (
        text[: option_match.start("settings")]
        + new_settings
        + text[option_match.end("settings") :]
    )
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_path = SETTINGS_INI.with_name(f"{SETTINGS_INI.name}.{timestamp}.bak")
    shutil.copy2(SETTINGS_INI, backup_path)
    temporary_path = SETTINGS_INI.with_name(f"{SETTINGS_INI.name}.palbot.tmp")
    try:
        temporary_path.write_text(updated_text, encoding="utf-8")
        os.replace(temporary_path, SETTINGS_INI)
    finally:
        temporary_path.unlink(missing_ok=True)
    return old_value, formatted_value, backup_path
