# Adding discord-mention-reminder-bot to a new server

One running bot handles every server it's in, and in each server it only has access to the channels you choose. Adding a server means getting the bot invited, giving it access to those channels, then adding their channel and role IDs to `config.json`.

## 1. Send the server admin an invite link

The bot works only in selected channels, so the invite grants **no server-wide permissions**:

```
https://discord.com/oauth2/authorize?client_id=1556418843063226458&scope=bot&permissions=0
```

## 2. Ask the admin to give the bot access to the chosen channels only

For **each channel to watch**, go to Edit Channel → **Permissions** → **Add members or roles**, choose the bot (or its role, which has the same name), and set these to ✅ **Allow**:

- View Channel
- Send Messages
- Read Message History

**Hiding it from other channels:** any channel that `@everyone` can see, the bot can see too. To make sure it can't, the admin sets **View Channel** to ❌ **Deny** for the bot in those channels (or on their categories). Either way, the bot only acts on the channels listed in `config.json` and ignores everything else.

**Also:** the role you'll tag either has **"Allow anyone to @mention this role"** turned on, or you have permission to mention it. Otherwise the tag isn't a real mention and the bot ignores it.

## 3. Copy the IDs

Turn on Developer Mode (User Settings → Advanced → Developer Mode), then right-click → **Copy ID** for:

- each **channel** to watch
- each **role** you'll tag
- each **user** who should acknowledge

## 4. Add them to `config.json`

Add the new channel to `channels` and the new role to `roles`, next to the entries that are already there:

```json
{
  "delay_hours": 24,
  "channels": ["<existing channel ID>", "<new channel ID>"],
  "authors": ["<your user ID>"],
  "roles": {
    "<existing role ID>": {"name": "TA", "users": ["<user ID>"]},
    "<new role ID>": {"name": "<label>", "users": ["<user ID>", "..."]}
  }
}
```

The bot pings only the users listed here, not everyone who actually has the role in Discord.

## 5. Restart the bot and check the startup output

```sh
cd discord-mention-reminder-bot
python3 reminder_bot.py      # reads DISCORD_TOKEN=<token> from .env
```

You should see:

```
  watching #<channel> (<new server>)
```

`WARNING: can't see channel <id>` means the channel ID is wrong or the bot is missing View Channel there.

If you shortened the timings for testing, set `"delay_hours": 24` and remove `check_minutes` before real use (see [README.md](README.md)).
