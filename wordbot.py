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

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

word_type = None
active_session = False
target_channel = None
twister_mode = False
twister_active = False  # <-- Added: to prevent overlapping twister rounds
used_words = set()
stop_signal = asyncio.Event()
words_per_round = WORDS_PER_ROUND
round_duration = ROUND_DURATION
word_lists = {}

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
        wt = fname[:-4]  # remove '.txt'
        all_words.extend(load_word_list(wt))
    random.shuffle(all_words)
    print(f"Total random words loaded: {len(all_words)}")
    return all_words

async def twister_countdown():
    progress_msg = await target_channel.send("🎤 Time left: [■■■■■■■■■■■■■■■■■■■■■■■■■■■■■ ] 30s")
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

    # Drop 3 twisters, 10 seconds apart
    for _ in range(3):
        twister = random.choice(twisters)
        await target_channel.send(twister)
        await twister_countdown()

    twister_mode = False
    twister_active = False
    stop_signal.clear()  # Clear stop signal to resume normal rounds

    await target_channel.send("🎤 Resuming word drop session...")

async def word_round():
    global word_type, used_words

    print(f"[DEBUG] Entered word_round(). twister_mode={twister_mode}, stop_signal={stop_signal.is_set()}")

    if twister_mode:
        print("[DEBUG] Twister mode is ON, skipping word round.")
        return  # twister runs separately in run_twisters

    if stop_signal.is_set():
        print("[DEBUG] Stop signal is set. Exiting word round.")
        return

    if word_type:
        words = load_word_list(word_type)
    else:
        words = load_random_words()

    words = [w for w in words if w not in used_words]

    if not words:
        used_words.clear()
        if word_type:
            words = load_word_list(word_type)
        else:
            words = load_random_words()
        words = [w for w in words if w not in used_words]

    if not words:
        await target_channel.send("No words found to drop.")
        return

    await target_channel.send("Dropping words, _Lets L I F T⬇️_")

    start_time = asyncio.get_event_loop().time()
    interval = round_duration / max(words_per_round, 1)

    words_dropped = 0
    while words_dropped < words_per_round and (asyncio.get_event_loop().time() - start_time < round_duration):
        if stop_signal.is_set():
            print("[DEBUG] Stop signal triggered during word drop.")
            return
        word = random.choice(words)
        used_words.add(word)
        await target_channel.send(f"🔹{word}🔹")
        words_dropped += 1
        await asyncio.sleep(interval)

    await target_channel.send("**🔥 Sheesh, fire!! Time to pass the Metal! 🔁**")
    await asyncio.sleep(5)

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
    global words_per_round, round_duration, stop_signal, used_words

    if message.author == client.user:
        return

    content = message.content.lower()

    if message.channel.id == TARGET_CHANNEL_ID and content.startswith("+"):
        try:
            if message.channel.permissions_for(message.guild.me).manage_messages:
                await message.delete()
        except Exception:
            pass

    if content.startswith("+start") and not active_session:
        active_session = True
        stop_signal.clear()
        used_words.clear()
        await message.channel.send("🎤 Starting word drop session...")
        while active_session:
            await word_round()

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

    elif content.startswith("+syllables"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            syll_num = parts[1]
            if 1 <= int(syll_num) <= 12:
                word_type = f"syllables {syll_num}"
                await message.channel.send(f"Loading words with **{syll_num} syllable(s)** in next round...")
            else:
                await message.channel.send("Please specify syllables between 1 and 12.")
        else:
            await message.channel.send("Usage: `+syllables 1` to `+syllables 12`")

    elif content.startswith("+twisters"):
        if twister_active:
            await message.channel.send("A twister round is already running. Please wait.")
            return
        twister_mode = True
        stop_signal.set()
        await run_twisters()

    elif content.startswith("+reset"):
        active_session = False
        word_type = None
        twister_mode = False
        stop_signal.clear()
        used_words.clear()
        print("🧹 Full reset: active_session=False, twister_mode=False, stop_signal cleared.")
        await message.channel.send("Words reset ♻️")

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
