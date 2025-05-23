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
twister_mode = False        # True while twister is ongoing
twister_cooldown = False    # Prevents triggering twister twice per round
twister_triggered = False   # Whether twister triggered in current round

word_lists = {}
used_words = set()
stop_signal = asyncio.Event()

words_per_round = WORDS_PER_ROUND
round_duration = ROUND_DURATION

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

async def run_twisters_once():
    global twister_mode, twister_cooldown, twister_triggered, target_channel

    if twister_cooldown:
        await target_channel.send("Twister already triggered recently! Please wait.")
        return
    twister_cooldown = True
    twister_mode = True
    twister_triggered = True

    twisters = load_word_list("twisters")
    if not twisters:
        await target_channel.send("No tongue twisters found.")
        twister_mode = False
        twister_cooldown = False
        return

    first_twister = random.choice(twisters)
    await target_channel.send("🎤 Here comes a twister!")
    await target_channel.send(f"🔁 {first_twister}")

    countdown = 30
    bar_length = 30
    full_block = "■"
    empty_block = " "
    bar = full_block * bar_length

    try:
        msg = await target_channel.send(f"🎤 Time left: [{bar}] {countdown}s")
    except Exception as e:
        print(f"Failed to send countdown message: {e}")
        twister_mode = False
        twister_cooldown = False
        return

    for elapsed in range(countdown):
        await asyncio.sleep(1)
        remaining = countdown - elapsed - 1
        filled_length = max(remaining, 0)
        empty_length = bar_length - filled_length
        bar = full_block * filled_length + empty_block * empty_length
        try:
            await msg.edit(content=f"🎤 Time left: [{bar}] {remaining}s")
        except Exception as e:
            print(f"Failed to edit countdown message at {remaining}s: {e}")

    await target_channel.send("🎬 Back to the word drops...")

    # Reset flags to allow normal word dropping again
    twister_mode = False

    # Cooldown to prevent immediate retrigger, but allow next round twister
    # After 30 seconds cooldown, allow twister again
    async def reset_cooldown():
        await asyncio.sleep(30)
        global twister_cooldown, twister_triggered
        twister_cooldown = False
        twister_triggered = False

    asyncio.create_task(reset_cooldown())

async def word_round():
    global word_type, used_words, twister_mode

    # If twister mode is active, skip word dropping (wait)
    if twister_mode:
        await asyncio.sleep(1)  # Just wait a bit before checking again
        return

    if word_type:
        words = load_word_list(word_type)
    else:
        words = load_random_words()

    # Filter out used words
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
        if stop_signal.is_set() or twister_mode:
            # If stopped or twister mode started, break early
            break
        word = random.choice(words)
        used_words.add(word)
        await target_channel.send(f"🔹{word}🔹")
        words_dropped += 1
        await asyncio.sleep(interval)

    if not twister_mode:
        await target_channel.send("**🔥 Sheesh, fire!! Time to pass the Metal! 🔁**")

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
    global word_type, active_session, target_channel, twister_mode, twister_cooldown
    global words_per_round, round_duration, stop_signal, used_words

    if message.author == client.user:
        return

    content = message.content.lower()

    # Delete command messages only if in target channel and start with '+'
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
        if not twister_mode and not twister_cooldown:
            stop_signal.set()  # stop any current round immediately
            stop_signal.clear()  # immediately clear so word_round can resume after twister
            # Run twister as a separate task so it doesn't block main loop
            asyncio.create_task(run_twisters_once())
        else:
            await message.channel.send("Twister already active or cooling down, please wait.")

    elif content.startswith("+reset"):
        word_type = None
        twister_mode = False
        twister_cooldown = False
        stop_signal.clear()
        used_words.clear()
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
