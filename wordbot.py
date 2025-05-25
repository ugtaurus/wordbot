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
SUFFIX_FOLDER = os.path.join(WORD_BANK_PATH, "suffixes")

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

suffix_descriptions = {
    "-ness": "state of being",
    "-acy": "quality",
    "-ist": "person",
    "-al": "process of",
    "-en": "make or become",
    "-tion": "state of being",
    "-ise": "make or become",
    "-or": "person",
    "-ty": "quality of",
    "-ment": "condition",
    "-dom": "state of being",
    "-ence": "quality",
    "-fy": "make or become",
    "-ate": "make or become",
    "-ism": "belief",
    "-ship": "position held",
    "-er": "the object that does a specified action",
    "-ance": "state",
    "-ible": "ability",
    "-ish": "a little",
    "-able": "able to be",
    "-some": "a tendency to",
    "-ful": "full of",
    "-like": "similar to",
    "-less": "without",
    "-ous": "full of",
    "-ly": "in a manner",
    "-ward": "shows direction",
    "-wise": "in a manner of",
    "-ways": "shows direction"
}

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
rhyme_mode_first_round = True
persistent_rhyme_files_used = set()

queue_twister_round = False

queue_suffix_round = False
queued_suffix_file = None

queue_persistent_suffix_mode = False
persistent_suffix_files_used = set()
suffix_mode_first_round = True

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
    return words

def load_random_words():
    all_words = []
    for fname in WORD_FILES_RANDOM:
        wt = fname[:-4]
        all_words.extend(load_word_list(wt))
    random.shuffle(all_words)
    return all_words

async def run_twister(twister_text):
    def build_flame_bar(seconds):
        flames = seconds // 5
        dashes = 6 - flames
        fire = "🔥"
        return f"|{fire * flames}{'-' * dashes}|"

    msg = await target_channel.send(f"**💅Twister Time!**\n_{twister_text}_")
    for second in range(1, 31):
        bar = build_flame_bar(second)
        await asyncio.sleep(1)
        if second == 30:
            await msg.edit(content=f"**💅Twister Time!**\n_{twister_text}_\n{bar} 30s  `sick!`")
        else:
            await msg.edit(content=f"**💅Twister Time!**\n_{twister_text}_\n{bar} {second}")

async def suffix_round(suffix_file, persistent_mode=False):
    global suffix_mode_first_round

    file_path = os.path.join(SUFFIX_FOLDER, suffix_file)
    with open(file_path, "r", encoding="utf-8") as f:
        suffix_words = [line.strip() for line in f if line.strip()]

    if not suffix_words:
        await target_channel.send("⚠️ Suffix file was empty.")
        return

    key = "-" + suffix_file.replace(".txt", "")
    meaning = suffix_descriptions.get(key, f"`{key}`")

    if persistent_mode:
        if suffix_mode_first_round:
            await target_channel.send(f"📸 Suffix Mode start! {meaning}")
            suffix_mode_first_round = False
        else:
            await target_channel.send(f"📸 More suffixes coming: {meaning}")
    else:
        await target_channel.send(f"📸 Suffix round queued! {meaning}")

    count_msg = await target_channel.send(f"📸 Suffix: {meaning} `3`")
    for count in ["2", "1", "GO!"]:
        await asyncio.sleep(1)
        await count_msg.edit(content=f"📸 Suffix: {meaning} `{count}`")

    interval = round_duration / max(words_per_round, 1)
    for _ in range(min(words_per_round, len(suffix_words))):
        word = random.choice(suffix_words)
        await target_channel.send(f"📸 {word}")
        await asyncio.sleep(interval)

    if not persistent_mode:
        await target_channel.send("📸 Suffix round done! Back to normal words...")

def clear_suffix_queue():
    global queue_suffix_round, queued_suffix_file
    queue_suffix_round = False
    queued_suffix_file = None

async def word_round():
    global queue_suffix_round, queued_suffix_file
    global queue_persistent_suffix_mode, persistent_suffix_files_used, suffix_mode_first_round
    global queue_twister_round

    if stop_signal.is_set():
        return

    if queue_twister_round:
        queue_twister_round = False
        await twister_round()
        return

    if queue_persistent_suffix_mode:
        suffix_files = [f for f in os.listdir(SUFFIX_FOLDER) if f.endswith(".txt")]
        available_files = [f for f in suffix_files if f not in persistent_suffix_files_used]
        if not available_files:
            persistent_suffix_files_used.clear()
            available_files = suffix_files

        chosen_file = random.choice(available_files)
        persistent_suffix_files_used.add(chosen_file)
        await suffix_round(chosen_file, persistent_mode=True)
        return

    if queue_suffix_round and queued_suffix_file:
        await suffix_round(queued_suffix_file, persistent_mode=False)
        clear_suffix_queue()
        return

    words = load_random_words()
    words = [w for w in words if w not in used_words]

    if not words:
        used_words.clear()
        words = load_random_words()
        words = [w for w in words if w not in used_words]

    if not words:
        await target_channel.send("No words found to drop.")
        return

    await target_channel.send("Dropping words, Lets `L I F T` :man_lifting_weights:")
    interval = round_duration / max(words_per_round, 1)

    for _ in range(words_per_round):
        word = random.choice(words)
        used_words.add(word)
        await target_channel.send(f"🔹{word}🔹")
        await asyncio.sleep(interval)

    await target_channel.send("**♨️ Sheesh, fire!! Time to pass the Metal! 🔁**")
    await asyncio.sleep(5)

async def word_drop_loop():
    global active_session
    while active_session:
        if stop_signal.is_set():
            await asyncio.sleep(1)
            continue
        await word_round()

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
    global active_session, stop_signal, current_task
    global queue_suffix_round, queued_suffix_file
    global queue_persistent_suffix_mode, persistent_suffix_files_used, suffix_mode_first_round

    if message.author == client.user:
        return

    if message.content.startswith("+start"):
        if not active_session:
            stop_signal.clear()
            active_session = True
            current_task = asyncio.create_task(word_drop_loop())
            await message.channel.send("✅ Word drop session started!")
        else:
            await message.channel.send("⚠️ Session already running.")

    elif message.content.startswith("+stop"):
        stop_signal.set()
        active_session = False
        await message.channel.send("🚛 Session stopped.")

    elif message.content.startswith("+suffix"):
        suffix_files = [f for f in os.listdir(SUFFIX_FOLDER) if f.endswith(".txt")]
        if not suffix_files:
            await message.channel.send("⚠️ No suffix files found.")
            return
        queued_suffix_file = random.choice(suffix_files)
        queue_suffix_round = True
        await message.channel.send("📸 Suffix round queued!")

    elif message.content.startswith("+suffix mode"):
        queue_persistent_suffix_mode = True
        persistent_suffix_files_used.clear()
        suffix_mode_first_round = True
        await message.channel.send("📸 Persistent suffix mode activated!")

client.run(TOKEN)
                        
