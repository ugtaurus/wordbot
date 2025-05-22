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
TWISTER_WAIT = 150  # 150 seconds wait between twisters
WORD_BANK_PATH = "wordbanks"

# ---------- GLOBALS ---------- #
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

word_type = None
target_channel = None
word_lists = {}
used_words = set()

# Control variables
session_task = None          # Background task for session (word drop or twister loop)
stop_signal = asyncio.Event()
mode = 'drop'                # Modes: 'drop' or 'twister_loop'

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

async def drop_word(target_channel):
    global word_type, used_words
    words = load_word_list(word_type) if word_type else load_all_words()
    words = [w for w in words if w not in used_words]
    if not words:
        used_words.clear()
        words = load_word_list(word_type) if word_type else load_all_words()
        words = [w for w in words if w not in used_words]
    word = random.choice(words)
    used_words.add(word)
    await target_channel.send(f"🔹{word}🔹")

async def drop_words_session():
    """Continuously drops words every interval unless stopped or mode changes."""
    global target_channel, stop_signal, mode, words_per_round, round_duration

    interval = round_duration / max(words_per_round, 1)

    while not stop_signal.is_set() and mode == 'drop':
        await target_channel.send("Dropping words, _Lets L I F T⬇️_")
        words_dropped = 0
        start_time = asyncio.get_event_loop().time()
        while (words_dropped < words_per_round
               and (asyncio.get_event_loop().time() - start_time) < round_duration
               and not stop_signal.is_set()
               and mode == 'drop'):
            await drop_word(target_channel)
            words_dropped += 1
            await asyncio.sleep(interval)

        if stop_signal.is_set() or mode != 'drop':
            break

        await target_channel.send("**🔥 Sheesh, fire!! Time to pass the Metal! 🔁**")
        await asyncio.sleep(2)  # brief pause before next round

async def drop_twister(target_channel):
    twisters = load_word_list("twisters")
    if not twisters:
        await target_channel.send("No tongue twisters found.")
        return
    twister = random.choice(twisters)
    await target_channel.send(f"**{twister}**")
    await asyncio.sleep(5)  # 5 sec delay after twister drop

async def twister_loop():
    """Loop of: twister1, wait 150s, twister2, wait 150s, then resume word drops. Repeat forever."""
    global stop_signal, target_channel, mode

    twisters = load_word_list("twisters")
    if not twisters:
        await target_channel.send("No tongue twisters found. Cancelling twister mode.")
        mode = 'drop'
        return

    await target_channel.send("🎤 Tongue Twister mode activated! Intermission starts now... 🔄")

    mode = 'twister_loop'
    while not stop_signal.is_set() and mode == 'twister_loop':
        # Twister 1
        await drop_twister(target_channel)
        if stop_signal.is_set():
            break
        try:
            await asyncio.wait_for(stop_signal.wait(), timeout=TWISTER_WAIT)
            break
        except asyncio.TimeoutError:
            pass  # timeout, continue

        if stop_signal.is_set():
            break

        # Twister 2
        await drop_twister(target_channel)
        if stop_signal.is_set():
            break
        try:
            await asyncio.wait_for(stop_signal.wait(), timeout=TWISTER_WAIT)
            break
        except asyncio.TimeoutError:
            pass  # timeout, continue

        if stop_signal.is_set():
            break

        # After two twisters + waits, resume word drop session for a short burst
        mode = 'drop'
        word_drop_cycles = 1  # number of word drop rounds before next twister cycle

        for _ in range(word_drop_cycles):
            if stop_signal.is_set() or mode != 'drop':
                break
            await drop_words_session()

        # Then back to twister loop
        mode = 'twister_loop'

    mode = 'drop'  # Ensure mode resets after stopping twister loop


async def start_session():
    """Start the default word drop session loop."""
    global stop_signal, mode
    mode = 'drop'
    stop_signal.clear()
    while not stop_signal.is_set():
        if mode == 'drop':
            await drop_words_session()
        elif mode == 'twister_loop':
            await twister_loop()
        else:
            # Unknown mode: default to drop
            mode = 'drop'


@client.event
async def on_ready():
    global target_channel, session_task
    target_channel = client.get_channel(TARGET_CHANNEL_ID)
    if target_channel:
        print(f"Logged in as {client.user}! Posting words in channel: {target_channel.name}")
        # Start initial word drop session task
        global stop_signal, mode, session_task
        stop_signal.clear()
        mode = 'drop'
        session_task = asyncio.create_task(start_session())
    else:
        print("⚠️ Bot logged in, but the channel was not found. Check the channel ID and bot permissions.")


@client.event
async def on_message(message):
    global word_type, stop_signal, mode, session_task, words_per_round, round_duration

    if message.author == client.user:
        return

    content = message.content.lower()

    async def try_delete():
        try:
            await message.delete()
        except:
            pass

    if content.startswith("+start"):
        await try_delete()
        if session_task and not session_task.done():
            await message.channel.send("Session already running!")
            return
        stop_signal.clear()
        mode = 'drop'
        session_task = asyncio.create_task(start_session())
        await message.channel.send("🎤 Starting word drop session...")

    elif content.startswith("+stop"):
        await try_delete()
        if session_task:
            stop_signal.set()
            try:
                await session_task
            except asyncio.CancelledError:
                pass
            session_task = None
            await message.channel.send("🛑 Word drop session force-stopped.")
        else:
            await message.channel.send("No active session to stop.")

    elif content.startswith("+reset"):
        await try_delete()
        stop_signal.set()       # stop anything running
        if session_task:
            try:
                await session_task
            except asyncio.CancelledError:
                pass
            session_task = None
        word_type = None
        mode = 'drop'
        stop_signal.clear()
        session_task = asyncio.create_task(start_session())
        await message.channel.send("Session reset: words only now ♻️")

    elif content.startswith("+twister"):
        await try_delete()
        if session_task:
            stop_signal.set()
            try:
                await session_task
            except asyncio.CancelledError:
                pass
            session_task = None
        stop_signal.clear()
        mode = 'twister_loop'
        session_task = asyncio.create_task(start_session())
        await message.channel.send("🎤 Starting Twister mode with automatic repeat!")

    elif content.startswith("+nouns"):
        await try_delete()
        word_type = "nouns"
        await message.channel.send("Loading **nouns** in next rounds...")

    elif content.startswith("+verbs"):
        await try_delete()
        word_type = "verbs"
        await message.channel.send("Loading **verbs** in next rounds...")

    elif content.startswith("+adjectives"):
        await try_delete()
        word_type = "adjectives"
        await message.channel.send("Loading **adjectives** in next rounds...")

    elif content.startswith("+adverbs"):
        await try_delete()
        word_type = "adverbs"
        await message.channel.send("Loading **adverbs** in next rounds...")

    elif content.startswith("+prepositions"):
        await try_delete()
        word_type = "prepositions"
        await message.channel.send("Loading **prepositions** in next rounds...")

    elif content.startswith("+conjunctions"):
        await try_delete()
        word_type = "conjunctions"
        await message.channel.send("Loading **conjunctions** in next rounds...")

    elif content.startswith("+wordcount"):
        await try_delete()
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            words_per_round = int(parts[1])
            await message.channel.send(f"Words per round set to **{words_per_round}**.")
        else:
            await message.channel.send("Usage: `+wordcount 5`")

    elif content.startswith("+wordtime"):
        await try_delete()
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            round_duration = int(parts[1])
            await message.channel.send(f"Round duration set to **{round_duration} seconds**.")
        else:
            await message.channel.send("Usage: `+wordtime 30`")


# ---------- RUN ---------- #
client.run(TOKEN)
