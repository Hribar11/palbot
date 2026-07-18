# PalBot

A small Discord bot that starts, stops, and monitors a Palworld dedicated server running on the same Windows machine.

## Project structure

```text
bot.py                      Minimal application entry point
palbot/settings.py          Environment variables and paths
palbot/server.py            Process control and Palworld REST API
palbot/ini_editor.py        Validated INI reading, editing, and backups
palbot/permissions.py       Player/admin role checks
palbot/client.py            Discord client and command synchronization
palbot/commands/start.py    /palstart
palbot/commands/stop.py     /palstop
palbot/commands/status.py   /palstatus
palbot/commands/stats.py    /palstats
palbot/commands/help.py     /palhelp
palbot/commands/palconfig.py  /palconfig command group
```

## Commands

- `/palstart` — starts the configured server executable
- `/palstop` — saves the world and gracefully shuts down the server
- `/palstatus` — reports whether it is running
- `/palstats` — shows players, FPS, frame time, uptime, world days, and base camps
- `/palhelp` — lists every available command
- `/palconfig get parameter` — reads a supported INI setting (admins only)
- `/palconfig set parameter value` — validates and changes a setting (admins only)
- `/palconfig list` — lists editable settings and their allowed values (admins only)

Members with either the `Palworld Players` or `Palworld Admins` role can start, stop, and inspect the server. Only `Palworld Admins` can edit settings. `/palhelp` is available to everyone. Role names are configurable and replies are private (ephemeral).

## Set up Discord

1. Open the [Discord Developer Portal](https://discord.com/developers/applications), create an application, and add a bot.
2. Copy the bot token. Never post or commit it.
3. Under **OAuth2 > URL Generator**, select `bot` and `applications.commands`. The bot needs no Discord permissions beyond **View Channels**. Open the generated URL to invite it.
4. In Discord, enable Developer Mode, right-click your server, and choose **Copy Server ID**.
5. Create `Palworld Players` and `Palworld Admins` roles. Give the admin role only to people trusted to change server settings.

## Install on the Windows server

Install Python 3.11 or newer, then open PowerShell in this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python bot.py
```

Set `PALSERVER_EXE` to the top-level `PalServer.exe`, set `PALSERVER_WORKING_DIR` to the installation directory containing it, and copy any existing launch arguments into `PALSERVER_ARGS`:

```env
PALSERVER_EXE=C:\PalworldServer\PalServer.exe
PALSERVER_WORKING_DIR=C:\PalworldServer
```

Set the role names and active INI path in `.env`:

```env
PALWORLD_PLAYER_ROLE_NAME=Palworld Players
PALWORLD_ADMIN_ROLE_NAME=Palworld Admins
PALWORLD_SETTINGS_INI=C:\PalworldServer\Pal\Saved\Config\WindowsServer\PalWorldSettings.ini
```

### Edit settings from Discord

Admins can use `/palconfig list`, `/palconfig get`, and `/palconfig set`. Discord autocompletes the supported parameter names and common values. Numeric ranges, booleans, and fixed choices are checked before the file is changed.

For safety, configuration changes are accepted only while Palworld is stopped. Each successful edit creates a timestamped `.bak` file next to `PalWorldSettings.ini`; start the server afterward to apply the new value. Secret and infrastructure settings—including passwords, REST API options, ports, and arbitrary INI text—cannot be changed through Discord.

### Enable safe saving and shutdown

Edit the active Windows server configuration, normally:

```text
Pal\Saved\Config\WindowsServer\PalWorldSettings.ini
```

If that file is empty, fully stop Palworld and copy the supplied defaults from the installation directory:

```powershell
Copy-Item `
  .\DefaultPalWorldSettings.ini `
  .\Pal\Saved\Config\WindowsServer\PalWorldSettings.ini `
  -Force
```

Inside its `OptionSettings=(...)` value, set these fields:

```text
RESTAPIEnabled=True,RESTAPIPort=8212,AdminPassword="choose-a-strong-password"
```

Preserve the other settings already present on that same line. Restart Palworld once after changing the file. Then put the same admin password in the bot's `.env`:

```env
PAL_REST_API_URL=http://127.0.0.1:8212/v1/api
PAL_REST_API_USER=admin
PAL_REST_API_PASSWORD=choose-a-strong-password
```

Keep port 8212 blocked from the public Internet. The bot and Palworld run on the same Windows host, so localhost access is sufficient.

When `DISCORD_GUILD_ID` is set, the commands normally appear in that server within seconds. Global command registration can take longer.

## Run automatically after reboot

Use Windows Task Scheduler:

1. Create a task triggered **At startup**.
2. Select **Run whether user is logged on or not**.
3. Set **Program/script** to the full path to `.venv\Scripts\python.exe`.
4. Set **Add arguments** to the full path to `bot.py`.
5. Set **Start in** to this project folder.

Run the task as the same Windows account that owns/runs the Palworld server. Do not run it as Administrator unless the existing server setup actually requires that.

## Shutdown behavior

`/palstop` calls Palworld's local REST API to save the world and schedule a graceful shutdown. If the API cannot be reached or rejects authentication, the bot reports the error and leaves the process running. After Palworld accepts the shutdown, the bot waits for `SHUTDOWN_DELAY_SECONDS + STOP_TIMEOUT_SECONDS`; it only terminates the process tree if that accepted graceful shutdown gets stuck.
