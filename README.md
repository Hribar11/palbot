# PalBot

A small Discord bot that starts, stops, and checks a Palworld dedicated server running on the same Windows machine.

## Commands

- `/palstart` — starts the configured server executable
- `/palstop` — saves the world and gracefully shuts down the server
- `/palstatus` — reports whether it is running

Only members with the configured Discord role can use these commands. Replies are private (ephemeral).

## Set up Discord

1. Open the [Discord Developer Portal](https://discord.com/developers/applications), create an application, and add a bot.
2. Copy the bot token. Never post or commit it.
3. Under **OAuth2 > URL Generator**, select `bot` and `applications.commands`. The bot needs no Discord permissions beyond **View Channels**. Open the generated URL to invite it.
4. In Discord, enable Developer Mode, right-click your server, and choose **Copy Server ID**.
5. Create a role such as `Palworld Admin` and give it only to trusted members.

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

Set `PALSERVER_EXE` to the actual executable used by your current Palworld launch script. Depending on the installation, this may instead be a top-level `PalServer.exe`. Set `PALSERVER_WORKING_DIR` to its containing folder and copy any launch arguments into `PALSERVER_ARGS`.

### Enable safe saving and shutdown

Edit the active Windows server configuration, normally:

```text
Pal\Saved\Config\WindowsServer\PalWorldSettings.ini
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
