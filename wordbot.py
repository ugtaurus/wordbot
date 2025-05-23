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
WORD_BANK_PATH = "wordbanks"

# ---------- GLOBALS ---------- #
WORD_FILES_RANDOM = [
    "adjectives.txt",
    "adverbs.txt",
    "conjunctions.txt",
    "nouns.txt",
    "prepositions.txt",
    "syllables 1.txt",
    "syllables 3.txt"
]

RHYME_FILES = [
    "rhymes bear.txt",
    "rhymes bet.txt",
    "rhymes boy.txt",
    "rhymes cake.txt",
    "rhymes cat.txt",
    "rhymes dog.txt",
    "rhymes ear.txt",
    "rhymes eye.txt",
    "rhymes jar.txt",
    "rhymes oh.txt",
    "rhymes ouch.txt",
    "rhymes screw.txt",
    "rhymes sun.txt",
    "rhymes torch.txt",
    "rhymes tree.txt",
    "rhymes twitch.txt",
    "rhymes work.txt",
    "rhymes yum.txt"
]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

word_type = None
active_session = False
target_channel = None
twister_mode = False
twister_active = False
used_words = set()
stop_signal = asyncio.Event()
words_per_round = WORDS_PER_ROUND
round_duration = ROUND_DURATION
word_lists = {}

word_drop_task = None

# ---------- UTILS ---------- #
def load_word_list(word_type):
    if word_type in word_lists:
        return word_lists[word_type]

    filename = word_type + ".txt"
    file_path = os.path.join(WORD_BANK_PATH, filename)
    if not os.path.isfile(file_path):
        print(f"⚠️ Word file not found: {filename}")
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    random.shuffle(words)
    word_lists[word_type] = words
    print(f"Loaded {len(words)} words from {filename}")
    return words

def load_random_words():
    all_words = []
    for fname in WORD_FILES_RANDOM:
        wt = fname[:-4]
        all_words.extend(load_word_list(wt))
    random.shuffle(all_words)
    print(f"Total random words loaded: {len(all_words)}")
    return all_words

async def twister_countdown():
    progress_msg = await target_channel.send("🎤 Time left: [■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■] 30s")
    total_seconds = 30
    blocks_total = 30
    for seconds_left in range(total_seconds, 0, -1):
        blocks_filled = seconds_left
        blocks_empty = blocks_total - blocks_filled
        bar = '■' * blocks_filled + ' ' * blocks_empty
        try:
            await progress_msg.edit(content=f"🎤 Time left: [{bar}] {seconds_left}s")
        except Exception:
            pass
        await asyncio.sleep(1)
    try:
        await progress_msg.delete()
    except Exception:
        pass

async def run_twisters():
    global twister_mode, target_channel, twister_active
    if twister_active:
        await target_channel.send("A twister round is already active! Please wait for it to finish.")
        return

    twister_active = True

    twisters = load_word_list("twisters")
    if not twisters:
        await target_channel.send("No tongue twisters found.")
        twister_mode = False
        twister_active = False
        return

    twister_mode = True
    await target_channel.send("Here comes a twister!")

    for _ in range(3):
        twister = random.choice(twisters)
        await target_channel.send(twister)
        await twister_countdown()

    twister_mode = False
    twister_active = False
    stop_signal.clear()
    await target_channel.send("🎤 Resuming word drop session...")

async def word_round():
    global word_type, used_words

    if twister_mode or stop_signal.is_set():
        return

    if word_type:
        words = load_word_list(word_type)
    else:
        words = load_random_words()

    words = [w for w in words if w not in used_words]

    if not words:
        used_words.clear()
        words = load_word_list(word_type) if word_type else load_random_words()
        words = [w for w in words if w not in used_words]

    if not words:
        await target_channel.send("No words found to drop.")
        return

    await target_channel.send("Dropping words, _Lets L I F T🔻_")

    interval = round_duration / max(words_per_round, 1)

    for _ in range(words_per_round):
        if stop_signal.is_set():
            return
        word = random.choice(words)
        used_words.add(word)
        await target_channel.send(f"🔸{word}🔸")
        await asyncio.sleep(interval)

    await target_channel.send("**🔥 Sheesh, fire!! Time to pass the Metal! 🔁**")
    await asyncio.sleep(5)

async def word_drop_loop():
    while active_session:
        if stop_signal.is_set() or twister_mode:
            await asyncio.sleep(1)
            continue
        await word_round()

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
    global word_type, active_session, target_channel, twister_mode
    global words_per_round, round_duration, stop_signal, used_words, word_drop_task

    if message.author == client.user:
        return

    content = message.content.lower()

    if message.channel.id == TARGET_CHANNEL_ID and content.startswith("+"):
        try:
            if message.channel.permissions_for(message.guild.me).manage_messages:
                await message.delete()
        except Exception:
            pass

    if content.startswith("+start"):
        if active_session:
            await message.channel.send("A word drop session is already active.")
        else:
            active_session = True
            stop_signal.clear()
            used_words.clear()
            await message.channel.send("🎤 Starting word drop session...")
            word_drop_task = asyncio.create_task(word_drop_loop())

    elif content.startswith("+stop"):
        if active_session:
            active_session = False
            stop_signal.set()
            if word_drop_task:
                word_drop_task.cancel()
            await message.channel.send("🛑 Word drop session force-stopped.")
        else:
            await message.channel.send("No active session to stop.")

    elif content.startswith("+reset"):
        active_session = False
        word_type = None
        twister_mode = False
        stop_signal.clear()
        used_words.clear()
        if word_drop_task:
            word_drop_task.cancel()
        await message.channel.send("Words reset ♻️")

    elif content.startswith("+rhymes"):
        available_rhymes = [fname for fname in RHYME_FILES if os.path.isfile(os.path.join(WORD_BANK_PATH, fname))]
        if not available_rhymes:
            await message.channel.send("❌ No rhyme files found in wordbanks directory.")
            return

        chosen_file = random.choice(available_rhymes)
        rhyme_path = os.path.join(WORD_BANK_PATH, chosen_file)

        with open(rhyme_path, "r", encoding="utf-8") as f:
            rhyme_words = [line.strip() for line in f if line.strip()]

        if not rhyme_words:
            await message.channel.send(f"⚠️ File `{chosen_file}` is empty.")
            return

        rhyme_name = chosen_file.replace("rhymes ", "").replace(".txt", "")
        await message.channel.send(f"🎯 Dropping rhymes for **{rhyme_name}**...")

        interval = round_duration / max(words_per_round, 1)
        words_used = set()
        for _ in range(min(words_per_round, len(rhyme_words))):
            word = random.choice([w for w in rhyme_words if w not in words_used])
            words_used.add(word)
            await message.channel.send(f"🔸{word}🔸")
            await asyncio.sleep(interval)

        await message.channel.send("**🔥 Sheesh, fire!! Time to pass the Metal! 🔁**")

# ---------- RUN ---------- #
client.run(TOKEN)
