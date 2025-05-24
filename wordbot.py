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
used_words = set()
stop_signal = asyncio.Event()
words_per_round = WORDS_PER_ROUND
round_duration = ROUND_DURATION

word_lists = {}

current_task = None
queue_rhyme_round = False
queued_rhyme_file = None

queue_persistent_rhyme_mode = False
persistent_rhyme_files_used = set()
rhyme_mode_first_round = True

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

async def word_round():
    global word_type, used_words, queue_rhyme_round, queued_rhyme_file
    global queue_persistent_rhyme_mode, persistent_rhyme_files_used, rhyme_mode_first_round

    if stop_signal.is_set():
        return

    if queue_persistent_rhyme_mode:
        rhyme_files = [f for f in os.listdir(WORD_BANK_PATH) if f.startswith("rhymes") and f.endswith(".txt")]
        available_files = [f for f in rhyme_files if f not in persistent_rhyme_files_used]
        if not available_files:
            persistent_rhyme_files_used.clear()
            available_files = rhyme_files

        chosen_file = random.choice(available_files)
        persistent_rhyme_files_used.add(chosen_file)
        await rhyme_round(chosen_file, persistent_mode=True)
        return

    if queue_rhyme_round and queued_rhyme_file:
        await rhyme_round(queued_rhyme_file, persistent_mode=False)
        clear_rhyme_queue()
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

    await target_channel.send("Dropping words, Lets L I F T :man_lifting_weights:")

    start_time = asyncio.get_event_loop().time()
    interval = round_duration / max(words_per_round, 1)

    words_dropped = 0
    while words_dropped < words_per_round and (asyncio.get_event_loop().time() - start_time < round_duration):
        if stop_signal.is_set():
            return
        word = random.choice(words)
        used_words.add(word)
        await target_channel.send(f"🔹{word}🔹")
        words_dropped += 1
        await asyncio.sleep(interval)

    await target_channel.send("**:hotsprings: Sheesh, fire!! Time to pass the Metal! 🔁**")
    await asyncio.sleep(5)

async def rhyme_round(rhyme_file, persistent_mode=False):
    global words_per_round, round_duration, target_channel, rhyme_mode_first_round

    file_path = os.path.join(WORD_BANK_PATH, rhyme_file)
    with open(file_path, "r", encoding="utf-8") as f:
        rhyme_words = [line.strip() for line in f if line.strip()]

    if not rhyme_words:
        await target_channel.send("⚠️ Rhyme file was empty.")
        return

    if persistent_mode:
        if rhyme_mode_first_round:
            await target_channel.send("🎯 Dropping rhymes!")
            rhyme_mode_first_round = False
        else:
            await target_channel.send("**More rhymes loading:⬇️ **")
    else:
        await target_channel.send("**🎯 Dropping rhymes!**")

    await asyncio.sleep(2)

    start_time = asyncio.get_event_loop().time()
    interval = round_duration / max(words_per_round, 1)

    for _ in range(min(words_per_round, len(rhyme_words))):
        word = random.choice(rhyme_words)
        await target_channel.send(f"🔸{word}🔸")
        await asyncio.sleep(interval)

    if not persistent_mode:
        await target_channel.send("🎤 Rhyme round done! Back to normal words...")

def clear_rhyme_queue():
    global queue_rhyme_round, queued_rhyme_file
    queue_rhyme_round = False
    queued_rhyme_file = None

async def word_drop_loop():
    global active_session, stop_signal
    while active_session:
        if stop_signal.is_set():
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
    if message.author == client.user:
        return

    # The rest of your command handling block was complete in your last message.
    # Just be sure your "+twisters" command ends like this:

    # --- END OF +twisters command ---
    await asyncio.sleep(2)
    await run_twister(selected_twisters[1])
    stop_signal.clear()

# ---------- BOT RUN ---------- #
client.run(TOKEN)
