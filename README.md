# PalBot

A small Discord bot that starts, stops, and checks a Palworld dedicated server running on the same Windows machine.

## Commands

- `/palstart` — starts the configured server executable
- `/palstop` — terminates the server process tree
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
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python bot.py
```

Set `PALSERVER_EXE` to the actual executable used by your current Palworld launch script. Depending on the installation, this may instead be a top-level `PalServer.exe`. Set `PALSERVER_WORKING_DIR` to its containing folder and copy any launch arguments into `PALSERVER_ARGS`.

When `DISCORD_GUILD_ID` is set, the commands normally appear in that server within seconds. Global command registration can take longer.

## Run automatically after reboot

Use Windows Task Scheduler:

1. Create a task triggered **At startup**.
2. Select **Run whether user is logged on or not**.
3. Set **Program/script** to the full path to `.venv\Scripts\python.exe`.
4. Set **Add arguments** to the full path to `bot.py`.
5. Set **Start in** to this project folder.

Run the task as the same Windows account that owns/runs the Palworld server. Do not run it as Administrator unless the existing server setup actually requires that.

## Important shutdown note

`/palstop` asks the Palworld process tree to terminate, waits for `STOP_TIMEOUT_SECONDS`, and then force-kills anything left. Palworld may not save immediately before a process termination. For a public or important world, configure Palworld RCON and add a `Save`/`Shutdown` flow before relying on this command for routine shutdowns.

