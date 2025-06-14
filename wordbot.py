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
SUFFIX_BANK_PATH = os.path.join(WORD_BANK_PATH, "suffixes")

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

# --- New suffix mode globals ---
queue_persistent_suffix_mode = False
queued_suffix_mode = False  # <-- new variable to defer suffix mode
persistent_suffix_files_used = set()
suffix_mode_first_round = True
suffix_mode_active = False  # <-- to know when it's currently active

suffix_meanings = {
    "-able": "capable of",
    "-acy": "state or quality",
    "-al": "pertaining to",
    "-ance": "state or quality",
    "-ate": "cause to be",
    "-dom": "state or condition",
    "-en": "to make",
    "-ence": "state or quality",
    "-er": "one who",
    "-ful": "full of",
    "-fy": "to make",
    "-ible": "capable of",
    "-ise": "to make",
    "-ish": "having the quality of",
    "-ism": "doctrine or belief",
    "-ist": "one who practices",
    "-less": "without",
    "-like": "resembling",
    "-ly": "in the manner of",
    "-ment": "result or means",
    "-ness": "state or quality",
    "-or": "one who",
    "-ous": "full of",
    "-ship": "state or condition",
    "-some": "characterized by",
    "-tion": "act or state",
    "-ty": "quality of",
    "-ward": "direction",
    "-ways": "in the manner of",
    "-wise": "in the way of"
}

# Call this function to queue suffix mode
def queue_suffix_mode():
    global queued_suffix_mode
    queued_suffix_mode = True
    print("📌 Suffix mode queued for next round.")

# Call this at the start of each round
def handle_mode_activation():
    global queued_suffix_mode, suffix_mode_active, suffix_mode_first_round
    if queued_suffix_mode:
        suffix_mode_active = True
        suffix_mode_first_round = True
        queued_suffix_mode = False
        print("✅ Suffix mode activated.")
    else:
        suffix_mode_first_round = False

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

def get_suffix_files():
    try:
        files = [f for f in os.listdir(SUFFIX_BANK_PATH) if f.startswith("suffix ") and f.endswith(".txt")]
        return files
    except Exception as e:
        print(f"⚠️ Could not list suffix files: {e}")
        return []

async def run_twister(twister_text):
    def build_flame_bar(seconds):
        flames = seconds // 5
        dashes = 6 - flames
        return f"|{'🔥' * flames}{'-' * dashes}|"

    msg = await target_channel.send(f"**👅Twister Time!**\n_{twister_text}_")
    for second in range(1, 31):
        bar = build_flame_bar(second)
        number_box = f"{second}" if second < 30 else "30"
        await asyncio.sleep(1)
        if second == 30:
            await msg.edit(content=f"**👅Twister Time!**\n_{twister_text}_\n{bar} 30s  \\s i c k\\")
        else:
            await msg.edit(content=f"**👅Twister Time!**\n_{twister_text}_\n{bar} {number_box}")

async def twister_round():
    all_twisters = []
    for fname in os.listdir(WORD_BANK_PATH):
        if fname.startswith("twisters") and fname.endswith(".txt"):
            try:
                with open(os.path.join(WORD_BANK_PATH, fname), "r", encoding="utf-8") as f:
                    all_twisters += [line.strip() for line in f if line.strip()]
            except Exception as e:
                print(f"⚠️ Error reading {fname}: {e}")

    if len(all_twisters) < 2:
        await target_channel.send("❌ Not enough tongue twisters found.")
        return

    selected_twisters = random.sample(all_twisters, 2)

    await run_twister(selected_twisters[0])
    await asyncio.sleep(2)
    await run_twister(selected_twisters[1])
    await asyncio.sleep(2)

async def word_round():
    global word_type, used_words, queue_rhyme_round, queued_rhyme_file
    global queue_persistent_rhyme_mode, persistent_rhyme_files_used, rhyme_mode_first_round
    global queue_twister_round
    global queue_persistent_suffix_mode, persistent_suffix_files_used, suffix_mode_first_round

    if stop_signal.is_set():
        return

    if queue_twister_round:
        queue_twister_round = False
        await twister_round()
        return

    # Prioritize suffix mode if active
    if queue_persistent_suffix_mode:
        suffix_files = get_suffix_files()
        available_files = [f for f in suffix_files if f not in persistent_suffix_files_used]
        if not available_files:
            persistent_suffix_files_used.clear()
            available_files = suffix_files

        chosen_file = random.choice(available_files)
        persistent_suffix_files_used.add(chosen_file)
        await suffix_round(chosen_file, persistent_mode=True)
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

    await target_channel.send("Dropping words, Lets `L I F T` :man_lifting_weights:")

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

async def suffix_round(suffix_file, persistent_mode=False):
    global words_per_round, round_duration, target_channel, suffix_mode_first_round

    file_path = os.path.join(SUFFIX_BANK_PATH, suffix_file)
    with open(file_path, "r", encoding="utf-8") as f:
        suffix_words = [line.strip() for line in f if line.strip()]

    if not suffix_words:
        await target_channel.send("⚠️ Suffix file was empty.")
        return

    # Extract suffix key from filename, e.g. "suffix -able.txt" -> "-able"
    suffix_key = suffix_file.replace("suffix ", "").replace(".txt", "")
    meaning = suffix_meanings.get(suffix_key, "meaning unknown")

    if persistent_mode:
        if suffix_mode_first_round:
            # Countdown animation: "Droppin suffix rhymes, Get ready `3` `2` `1`"
            countdown_msg = await target_channel.send(f"**Droppin suffix rhymes, Get ready `3`**")
            await asyncio.sleep(1)
            await countdown_msg.edit(content=f"**Droppin suffix rhymes, Get ready `2`**")
            await asyncio.sleep(1)
            await countdown_msg.edit(content=f"**Droppin suffix rhymes, Get ready `1`**")
            await asyncio.sleep(1)
            await countdown_msg.edit(content=f"**Droppin suffix rhymes, GO!**")
            await asyncio.sleep(1)
            suffix_mode_first_round = False
        else:
            await target_channel.send("**Droppin Suffixes⬇️**")
    else:
        # For single suffix round (non-persistent) just send a quick message with suffix and meaning
        await target_channel.send(f"**Suffix Round: `{suffix_key}={meaning}`**")
        await asyncio.sleep(2)

    start_time = asyncio.get_event_loop().time()
    interval = round_duration / max(words_per_round, 1)

    # Drop words with low brightness effect using :low_brightness: emoji around word
    for _ in range(min(words_per_round, len(suffix_words))):
        word = random.choice(suffix_words)
        await target_channel.send(f":low_brightness:{word}:low_brightness:")
        await asyncio.sleep(interval)

    if not persistent_mode:
        await target_channel.send("🎤 Suffix round done! Back to normal words...")

def clear_rhyme_queue():
    global queue_rhyme_round, queued_rhyme_file
    queue_rhyme_round = False
    queued_rhyme_file = None

def clear_suffix_queue():
    global queue_persistent_suffix_mode, persistent_suffix_files_used, suffix_mode_first_round
    queue_persistent_suffix_mode = False
    persistent_suffix_files_used.clear()
    suffix_mode_first_round = True

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
    global word_type, active_session, target_channel
    global words_per_round, round_duration, stop_signal, used_words
    global queue_rhyme_round, queued_rhyme_file, current_task
    global queue_persistent_rhyme_mode, persistent_rhyme_files_used, rhyme_mode_first_round
    global queue_twister_round
    global queue_persistent_suffix_mode, persistent_suffix_files_used, suffix_mode_first_round

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
            clear_rhyme_queue()
            clear_suffix_queue()
            queue_persistent_rhyme_mode = False
            persistent_rhyme_files_used.clear()
            rhyme_mode_first_round = True
            queue_twister_round = False
            word_type = None

            countdown_message = await message.channel.send("**🎤 Starting word drop session in... `3**")
            await asyncio.sleep(1)
            await countdown_message.edit(content="**🎤 Starting word drop session in... `2`**")
            await asyncio.sleep(1)
            await countdown_message.edit(content="**🎤 Starting word drop session in... `1`**")
            await asyncio.sleep(1)
            await countdown_message.edit(content="**🎤 Starting word drop session in... `GO!`**")
            await asyncio.sleep(0.5)

            current_task = asyncio.create_task(word_drop_loop())

    elif content.startswith("+stop"):
        if active_session:
            active_session = False
            stop_signal.set()
            clear_rhyme_queue()
            clear_suffix_queue()
            queue_persistent_rhyme_mode = False
            persistent_rhyme_files_used.clear()
            rhyme_mode_first_round = True
            queue_twister_round = False
            if current_task:
                current_task.cancel()
                try:
                    await current_task
                except asyncio.CancelledError:
                    pass
                current_task = None
            await message.channel.send("🚓 Word drop session force-stopped.")
        else:
            await message.channel.send("No active session to stop.")

    elif content.startswith("+reset"):
        word_type = None
        clear_rhyme_queue()
        clear_suffix_queue()
        stop_signal.clear()
        used_words.clear()
        queue_persistent_rhyme_mode = False
        persistent_rhyme_files_used.clear()
        rhyme_mode_first_round = True
        queue_twister_round = False
        await message.channel.send("_♻️ Words reset_")

    elif content.startswith("+nouns"):
        word_type = "nouns"
        await message.channel.send("_Loading **nouns** in next round..._")

    elif content.startswith("+verbs"):
        word_type = "verbs"
        await message.channel.send("_Loading **verbs** in next round..._")

    elif content.startswith("+adjectives"):
        word_type = "adjectives"
        await message.channel.send("_Loading **adjectives** in next round..._")

    elif content.startswith("+adverbs"):
        word_type = "adverbs"
        await message.channel.send("_Loading **adverbs** in next round..._")

    elif content.startswith("+prepositions"):
        word_type = "prepositions"
        await message.channel.send("_Loading **prepositions** in next round..._")

    elif content.startswith("+conjunctions"):
        word_type = "conjunctions"
        await message.channel.send("_Loading **conjunctions** in next round..._")

    elif content.startswith("+syllables"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            syll_num = parts[1]
            if 1 <= int(syll_num) <= 12:
                word_type = f"syllables {syll_num}"
                await message.channel.send(f"_Loading **{syll_num} syllable(s)** words in next round..._")
            else:
                await message.channel.send("Please specify syllables between 1 and 12.")
        else:
            await message.channel.send("Usage: +syllables 1 to +syllables 12")

    elif content.startswith("+wordcount"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            words_per_round = int(parts[1])
            await message.channel.send(f"Words per round set to **{words_per_round}**.")
        else:
            await message.channel.send("Usage: +wordcount 5")

    elif content.startswith("+wordtime"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            round_duration = int(parts[1])
            await message.channel.send(f"Round duration set to **{round_duration} seconds**.")
        else:
            await message.channel.send("Usage: +wordtime 30")

    elif content.startswith("+rhymes"):
        rhyme_files = [f for f in os.listdir(WORD_BANK_PATH) if f.startswith("rhymes") and f.endswith(".txt")]
        if not rhyme_files:
            await message.channel.send("❌ No rhyme word files found.")
            return

        available_files = [f for f in rhyme_files if f != queued_rhyme_file]
        if not available_files:
            available_files = rhyme_files

        chosen_file = random.choice(available_files)
        queue_rhyme_round = True
        queued_rhyme_file = chosen_file
        await message.channel.send("Rhyme round queued!")

    elif content.startswith("+rhyme mode"):
        queue_persistent_rhyme_mode = not queue_persistent_rhyme_mode
        if queue_persistent_rhyme_mode:
            persistent_rhyme_files_used.clear()
            rhyme_mode_first_round = True
            await message.channel.send("🎤 Persistent rhyme mode activated.")
        else:
            await message.channel.send("🎤 Persistent rhyme mode deactivated.")

    elif content.startswith("+suffix"):
        suffix_files = get_suffix_files()
        if not suffix_files:
            await message.channel.send("❌ No suffix files found.")
            return

        available_files = [f for f in suffix_files if f != queued_rhyme_file]
        if not available_files:
            available_files = suffix_files

        chosen_file = random.choice(available_files)
        await suffix_round(chosen_file)

    elif content.startswith("+suffix mode"):
        queue_persistent_suffix_mode = not queue_persistent_suffix_mode
        if queue_persistent_suffix_mode:
            persistent_suffix_files_used.clear()
            suffix_mode_first_round = True
            await message.channel.send("🎤 Persistent suffix mode activated.")
        else:
            await message.channel.send("🎤 Persistent suffix mode deactivated.")

# ---------- BOT START ---------- #
keep_alive()
client.run(TOKEN)
