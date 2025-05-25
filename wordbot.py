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

queue_twister_round = False
queued_twisters = []

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
    global queue_twister_round, queued_twisters

    if stop_signal.is_set():
        return

    if queue_twister_round and len(queued_twisters) == 2:
        await run_twister(queued_twisters[0])
        await asyncio.sleep(2)
        await run_twister(queued_twisters[1])
        await asyncio.sleep(2)
        queue_twister_round = False
        queued_twisters = []
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

    await target_channel.send("Dropping words, Let's `L I F T` :man_lifting_weights:")

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

async def run_twister(twister_text):
    def build_flame_bar(seconds):
        flames = seconds // 5
        dashes = 6 - flames
        return "|" + "🔥" * flames + "-" * dashes + "|"

    msg = await target_channel.send(f"**👅Twister Time!**\n_{twister_text}_")
    for second in range(1, 31):
        bar = build_flame_bar(second)
        number_box = f"`{second}`"
        await asyncio.sleep(1)
        await msg.edit(content=f"**👅Twister Time!**\n_{twister_text}_\n{bar} {number_box}")

# PATCH FOR +twisters
@client.event
async def on_message(message):
    global queue_twister_round, queued_twisters
    if message.content.startswith("+twisters"):
        if not active_session:
            await message.channel.send("No active session to interrupt with tongue twisters.")
            return

        twister_file_path = os.path.join(WORD_BANK_PATH, "twisters.txt")
        if not os.path.isfile(twister_file_path):
            await message.channel.send("❌ `twisters.txt` not found in wordbank.")
            return

        try:
            with open(twister_file_path, "r", encoding="utf-8") as f:
                all_twisters = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"⚠️ Error reading twisters.txt: {e}")
            return

        if len(all_twisters) < 2:
            await message.channel.send("❌ Not enough tongue twisters found.")
            return

        queued_twisters = random.sample(all_twisters, 2)
        queue_twister_round = True
        await message.channel.send("👅 Two tongue twisters queued for next round!")

    # include original on_message logic here...

# make sure to call client.run(TOKEN) at the end
client.run(TOKEN)
