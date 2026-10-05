# discord-mention-reminder-bot

A Discord bot that follows up on role-tagged messages. When a message in one of the selected channels tags a configured role (e.g. `@TA please review`), the bot waits a set time (24h by default). It then replies once to that message, pinging everyone on the role's list who hasn't reacted 👍 (any skin tone counts).

- Works only in the channels you pick. It has no server-wide permissions.
- You keep each role's member list in `config.json`. The bot doesn't read server member lists.
- Reminders are stored in SQLite, so overdue ones are sent when the bot starts back up.

## Setup

1. **Create the bot.** In the [Developer Portal](https://discord.com/developers/applications), go to New Application → **Bot** → **Reset Token** and copy the token. No privileged intents are needed.
2. **Install:**
   ```sh
   git clone https://github.com/yididiya-isu/discord-mention-reminder-bot.git
   cd discord-mention-reminder-bot
   python3 -m pip install -r requirements.txt
   ```
3. **Add the token** to a `.env` file in the repo folder (git-ignored):
   ```
   DISCORD_TOKEN=<your bot token>
   ```
4. **Configure:** `cp config.example.json config.json`, then fill in the IDs. Turn on Developer Mode (User Settings → Advanced), then right-click a channel, role or user → **Copy ID**.

   | Key | Meaning |
   |---|---|
   | `delay_hours` | Hours to wait before reminding (default `24`) |
   | `check_minutes` | How often to check for due reminders (default `5`) |
   | `channels` | Channel IDs to watch. Threads inside them count too. Required. |
   | `authors` | Only track messages from these user IDs. `[]` means anyone. |
   | `roles` | `{role_id: {"name": ..., "users": [user_id, ...]}}`: who must 👍 for each role |

5. **Add the bot to a server:** follow [ADDING_A_SERVER.md](ADDING_A_SERVER.md).
6. **Run:**
   ```sh
   python3 reminder_bot.py
   ```
   To use a different config file, pass its path: `python3 reminder_bot.py config.3090.json`.
   Keep it on a machine that stays on. Messages posted while the bot is offline aren't tracked.

## Testing

Set `"delay_hours": 0.0167` and `"check_minutes": 1`, put your own user ID in `authors` and in a role's `users`, then tag that role in a watched channel:

- If you don't react, the bot should reply and ping you within about 2 minutes.
- If you react 👍, no reminder should come.
