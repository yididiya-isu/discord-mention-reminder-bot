"""discord-mention-reminder-bot: remind people who haven't acknowledged a role-tagged message with 👍.

Watches a short list of channels. When a message there tags one of your configured
roles, the bot waits `delay_hours`. It then replies once, pinging every user listed
for those roles who hasn't reacted 👍 (any skin tone).

Setup and server instructions: README.md and ADDING_A_SERVER.md.

Usage: python3 reminder_bot.py [config file]   (default: config.json next to this file)

config.json:
  delay_hours  hours to wait before reminding
  check_minutes  how often to look for due reminders (default 5)
  channels     channel IDs to watch (threads in them count too); must be non-empty
  authors      only track messages from these user IDs; [] = anyone
  roles        {role_id: {"name": ..., "users": [user_id, ...]}}, your hand-kept member lists
"""

import json
import os
import sqlite3
import sys
import time
import traceback

import discord
from discord.ext import tasks

HERE = os.path.dirname(os.path.abspath(__file__))

# Load KEY=VALUE lines from .env next to this file (real env vars take precedence).
ENV_PATH = os.path.join(HERE, ".env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            key, sep, value = line.strip().partition("=")
            if sep and not key.startswith("#"):
                os.environ.setdefault(key.strip(), value.strip().strip("'\""))
if "DISCORD_TOKEN" not in os.environ:
    raise SystemExit(f"DISCORD_TOKEN not set: add a line 'DISCORD_TOKEN=<token>' to {ENV_PATH}")
TOKEN = os.environ["DISCORD_TOKEN"]
# Config path: first command-line argument, else $REMINDER_CONFIG, else config.json next to this file.
CONFIG_PATH = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("REMINDER_CONFIG", os.path.join(HERE, "config.json"))
DB_PATH = os.environ.get("REMINDER_DB", os.path.join(HERE, "reminders.db"))

with open(CONFIG_PATH) as f:
    config = json.load(f)
DELAY_SECONDS = float(config.get("delay_hours", 24)) * 3600
CHECK_MINUTES = float(config.get("check_minutes", 5))
CHANNELS = {int(c) for c in config.get("channels", [])}
AUTHORS = {int(a) for a in config.get("authors", [])}
ROLES = {int(rid): {int(u) for u in r.get("users", [])} for rid, r in config.get("roles", {}).items()}
ROLE_NAMES = {int(rid): r.get("name", rid) for rid, r in config.get("roles", {}).items()}
if not CHANNELS:
    raise SystemExit(f"{CONFIG_PATH}: 'channels' must list at least one channel ID")

THUMBS_UP = {"👍"} | {"👍" + tone for tone in "\U0001F3FB\U0001F3FC\U0001F3FD\U0001F3FE\U0001F3FF"}

db = sqlite3.connect(DB_PATH)
db.execute(
    """CREATE TABLE IF NOT EXISTS tracked (
        message_id INTEGER PRIMARY KEY,
        channel_id INTEGER, guild_id INTEGER,
        role_ids TEXT, due_at REAL, done INTEGER DEFAULT 0
    )"""
)
db.commit()

intents = discord.Intents.none()
intents.guilds = True
intents.guild_messages = True
intents.guild_reactions = True
client = discord.Client(intents=intents)


def in_watched_channel(channel) -> bool:
    return channel.id in CHANNELS or getattr(channel, "parent_id", None) in CHANNELS


@client.event
async def on_ready():
    print(f"Logged in as {client.user} in {len(client.guilds)} server(s)")
    for cid in CHANNELS:
        ch = client.get_channel(cid)
        if ch:
            print(f"  watching #{ch.name} ({ch.guild.name})")
        else:
            print(f"  WARNING: can't see channel {cid} (wrong ID, or bot lacks View Channel)")


@client.event
async def on_message(msg: discord.Message):
    if msg.author == client.user or msg.guild is None or not in_watched_channel(msg.channel):
        return
    if AUTHORS and msg.author.id not in AUTHORS:
        return
    role_ids = [r.id for r in msg.role_mentions if r.id in ROLES]
    if not role_ids:
        return
    due_at = msg.created_at.timestamp() + DELAY_SECONDS
    db.execute(
        "INSERT OR IGNORE INTO tracked (message_id, channel_id, guild_id, role_ids, due_at) VALUES (?,?,?,?,?)",
        (msg.id, msg.channel.id, msg.guild.id, json.dumps(role_ids), due_at),
    )
    db.commit()
    names = ", ".join(ROLE_NAMES[r] for r in role_ids)
    print(f"tracking {msg.jump_url} [{names}], reminder due {time.strftime('%Y-%m-%d %H:%M', time.localtime(due_at))}")


async def acked_users(msg: discord.Message) -> set[int]:
    users = set()
    for reaction in msg.reactions:
        if str(reaction.emoji).replace("️", "") in THUMBS_UP:
            async for u in reaction.users():
                users.add(u.id)
    return users


async def remind(message_id: int, channel_id: int, role_ids: list[int]):
    try:
        channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
        msg = await channel.fetch_message(message_id)
    except (discord.NotFound, discord.Forbidden):
        print(f"message {message_id} gone or inaccessible; skipping")
        return

    expected = set().union(*(ROLES.get(r, set()) for r in role_ids))
    pending = sorted(expected - await acked_users(msg))
    if not pending:
        print(f"all acknowledged: {msg.jump_url}")
        return

    # Split into chunks that fit Discord's 2000-char limit.
    header = "⏰ Reminder: please 👍 to acknowledge —"
    chunks, line = [], header
    for uid in pending:
        mention = f" <@{uid}>"
        if len(line) + len(mention) > 2000:
            chunks.append(line)
            line = "⏰ (cont.)"
        line += mention
    chunks.append(line)
    for text in chunks:
        await msg.reply(text, mention_author=False,
                        allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
    print(f"reminded {len(pending)} user(s): {msg.jump_url}")


@tasks.loop(minutes=5)
async def check_due():
    rows = db.execute(
        "SELECT message_id, channel_id, role_ids FROM tracked WHERE done = 0 AND due_at <= ?",
        (time.time(),),
    ).fetchall()
    if rows:
        print(f"{len(rows)} reminder(s) due")
    for message_id, channel_id, role_ids in rows:
        try:
            await remind(message_id, channel_id, json.loads(role_ids))
        except Exception:
            # Never let one bad row kill the loop; retry it next check.
            print(f"error on {message_id}, will retry next check:")
            traceback.print_exc()
            continue
        db.execute("UPDATE tracked SET done = 1 WHERE message_id = ?", (message_id,))
        db.commit()


@check_due.before_loop
async def before_check_due():
    await client.wait_until_ready()


@check_due.error
async def check_due_error(error):
    print("reminder loop crashed; restarting:")
    traceback.print_exception(type(error), error, error.__traceback__)
    check_due.restart()


@client.event
async def setup_hook():
    check_due.change_interval(minutes=CHECK_MINUTES)
    check_due.start()  # first run happens right after login, catching up overdue reminders


client.run(TOKEN)
