from keep_alive import keep_alive
keep_alive()

import os
import discord
import asyncio
import random

TOKEN = os.getenv("TOKEN")

# ---------- SETTINGS ---------- #
TARGET_CHANNEL_ID = 1374368615138328656
WORDS_PER_ROUND = 5
ROUND_DURATION = 30
TWISTER_INTERVAL = 150  # seconds between twisters
SHEESH_DELAY = 5  # delay after Sheesh before next round
WORD_BANK_PATH = "wordbanks"

# ---------- GLOBALS ---------- #
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
client = discord.Client(intents=intents)

word_type = None
active_session = False
target_channel = None
twister_mode = False
word_lists = {}
used_words = set()
stop_signal = asyncio.Event()

words_per_round = WORDS_PER_ROUND
round_duration = ROUND_DURATION

# ---------- UTILS ---------- #
def load_word_list(word_type):
    if word_type in word_lists:
        return word_lists[word_type]

    file_path = os.path.join(WORD_BANK_PATH, f"{word_type}.txt")
    if not os.path.isfile(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    random.shuffle(words)
    word_lists[word_type] = words
    return words

def load_all_words():
    all_words = []
    for file in os.listdir(WORD_BANK_PATH):
        if file.endswith(".txt") and file != "twisters.txt":
            all_words.extend(load_word_list(file[:-4]))
    random.shuffle(all_words)
    return all_words

async def run_twisters():
    global twister_mode, target_channel
    twisters = load_word_list("twisters")
    if not twisters:
        await target_channel.send("No tongue twisters found.")
        return

    twister_mode = True
    await target_channel.send("🎤 Starting Twister mode with automatic repeat!")

    while twister_mode and not stop_signal.is_set():
        twister1 = random.choice(twisters)
        await target_channel.send(f"Here's a twister:\n**{twister1}**")
        await asyncio.sleep(TWISTER_INTERVAL)
        if stop_signal.is_set():
            break

        twister2 = random.choice(twisters)
        await target_channel.send(f"Here's another twister:\n**{twister2}**")
        await asyncio.sleep(TWISTER_INTERVAL)
        if stop_signal.is_set():
            break

        # After both twisters, break loop to resume normal word dropping
        break

    twister_mode = False

# ---------- WORD ROUND ---------- #
async def word_round():
    global word_type, target_channel, twister_mode, active_session, used_words

    words = load_word_list(word_type) if word_type else load_all_words()
    words = [word for word in words if word not in used_words]
    if not words:
        used_words.clear()
        words = load_word_list(word_type) if word_type else load_all_words()
        words = [word for word in words if word not in used_words]

    await target_channel.send("Dropping words, _Lets L I F T⬇️_")

    start_time = asyncio.get_event_loop().time()
    interval = round_duration / max(words_per_round, 1)

    words_dropped = 0
    while words_dropped < words_per_round and (asyncio.get_event_loop().time() - start_time < round_duration):
        if stop_signal.is_set() or twister_mode:
            return
        word = random.choice(words)
        used_words.add(word)
        await target_channel.send(f"🔹{word}🔹")
        words_dropped += 1
        await asyncio.sleep(interval)

    await target_channel.send("**🔥 Sheesh, fire!! Time to pass the Metal! 🔁**")
    await asyncio.sleep(SHEESH_DELAY)  # small delay after sheesh

# ---------- MAIN SESSION LOOP ---------- #
async def main_session_loop():
    global active_session, twister_mode

    while active_session and not stop_signal.is_set():
        if twister_mode:
            await run_twisters()
            if stop_signal.is_set():
                break
        else:
            await word_round()
            if stop_signal.is_set():
                break

        # Switch modes automatically
        # After word round, go to twister mode; after twister, back to word mode
        twister_mode = not twister_mode

    # Reset flags when done
    active_session = False
    twister_mode = False
    stop_signal.clear()

# ---------- EVENTS ---------- #
@client.event
async def on_ready():
    global target_channel
    target_channel = client.get_channel(TARGET_CHANNEL_ID)
    if target_channel:
        print(f"Logged in as {client.user}! Posting words in channel: {target_channel.name}")
    else:
        print("⚠️ Bot is logged in, but the channel was not found. Check the channel ID and bot permissions.")

@client.event
async def on_message(message):
    global word_type, active_session, twister_mode
    global words_per_round, round_duration, stop_signal

    if message.author == client.user:
        return

    content = message.content.lower()

    # Delete user command messages after processing, if bot has permissions
    try:
        await message.delete()
    except discord.Forbidden:
        # Bot lacks permission to delete messages, ignore
        pass
    except Exception:
        pass

    if content.startswith("+start") and not active_session:
        active_session = True
        stop_signal.clear()
        await message.channel.send("🎤 Starting word drop session...")
        client.loop.create_task(main_session_loop())

    elif content.startswith("+stop"):
        if active_session:
            active_session = False
            stop_signal.set()
            await message.channel.send("🛑 Word drop session force-stopped.")
        else:
            await message.channel.send("No active session to stop.")

    elif content.startswith("+nouns"):
        word_type = "nouns"
        await message.channel.send("Loading **nouns** in next round...")

    elif content.startswith("+verbs"):
        word_type = "verbs"
        await message.channel.send("Loading **verbs** in next round...")

    elif content.startswith("+adjectives"):
        word_type = "adjectives"
        await message.channel.send("Loading **adjectives** in next round...")

    elif content.startswith("+adverbs"):
        word_type = "adverbs"
        await message.channel.send("Loading **adverbs** in next round...")

    elif content.startswith("+prepositions"):
        word_type = "prepositions"
        await message.channel.send("Loading **prepositions** in next round...")

    elif content.startswith("+conjunctions"):
        word_type = "conjunctions"
        await message.channel.send("Loading **conjunctions** in next round...")

    elif content.startswith("+twisters"):
        if not active_session:
            await message.channel.send("Start a session first with +start.")
            return
        # Immediately switch to twister mode, interrupt word drops
        twister_mode = True
        stop_signal.clear()
        await message.channel.send("Switching to twister mode...")

    elif content.startswith("+reset"):
        word_type = None
        twister_mode = False
        stop_signal.set()
        active_session = False
        await message.channel.send("Reset done. Words and twister modes cleared.")

    elif content.startswith("+wordcount"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            words_per_round = int(parts[1])
            await message.channel.send(f"Words per round set to **{words_per_round}**.")
        else:
            await message.channel.send("Usage: `+wordcount 5`")

    elif content.startswith("+wordtime"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            round_duration = int(parts[1])
            await message.channel.send(f"Round duration set to **{round_duration} seconds**.")
        else:
            await message.channel.send("Usage: `+wordtime 30`")

# ---------- RUN ---------- #
client.run(TOKEN)
