from keep_alive import keep_alive
keep_alive()

import os
import discord
import asyncio
import random

TOKEN = os.getenv("TOKEN")

# ---------- SETTINGS ---------- #
TARGET_CHANNEL_IDS = [1374368615138328656, 1383360832112431206]
WORDS_PER_ROUND = 5
ROUND_DURATION = 30
WORD_BANK_PATH = "wordbanks"

# ---------- GLOBALS ---------- #
WORD_FILES_RANDOM = [
    "adjectives.txt", "adverbs.txt", "conjunctions.txt",
    "nouns.txt", "prepositions.txt", "syllables 1.txt", "syllables 3.txt"
]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

word_type = None
active_session = False
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

# ---------- HELPERS ---------- #
async def send_to_all_channels(msg):
    for channel_id in TARGET_CHANNEL_IDS:
        channel = client.get_channel(channel_id)
        if channel:
            try:
                await channel.send(msg)
            except Exception as e:
                print(f"Error sending to channel {channel_id}: {e}")

async def edit_all_messages(messages, new_content):
    for msg in messages:
        try:
            await msg.edit(content=new_content)
        except:
            pass

# ---------- UTILS ---------- #
def load_word_list(word_type):
    if word_type in word_lists:
        return word_lists[word_type]
    filename = word_type + ".txt"
    path = os.path.join(WORD_BANK_PATH, filename)
    if not os.path.exists(path):
        print(f"File missing: {filename}")
        return []
    with open(path, encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    random.shuffle(words)
    word_lists[word_type] = words
    return words

def load_random_words():
    all_words = []
    for fname in WORD_FILES_RANDOM:
        all_words.extend(load_word_list(fname[:-4]))
    random.shuffle(all_words)
    return all_words

async def run_twister(twister_text):
    def bar(sec): return f"|{'🔥'*(sec//5)}{'-'*(6-sec//5)}|"
    messages = []
    for cid in TARGET_CHANNEL_IDS:
        ch = client.get_channel(cid)
        if ch:
            msg = await ch.send(f"**👅Twister Time!**\n_{twister_text}_")
            messages.append(msg)
    for i in range(1, 31):
        flame = bar(i)
        new_txt = f"**👅Twister Time!**\n_{twister_text}_\n{flame} {i if i<30 else '30s  \\s i c k\\'}"
        await edit_all_messages(messages, new_txt)
        await asyncio.sleep(1)

async def twister_round():
    all_twisters = []
    for fname in os.listdir(WORD_BANK_PATH):
        if fname.startswith("twisters") and fname.endswith(".txt"):
            with open(os.path.join(WORD_BANK_PATH, fname), encoding="utf-8") as f:
                all_twisters += [line.strip() for line in f if line.strip()]
    if len(all_twisters) < 2:
        await send_to_all_channels("❌ Not enough tongue twisters.")
        return
    for twister in random.sample(all_twisters, 2):
        await run_twister(twister)
        await asyncio.sleep(2)

def clear_rhyme_queue():
    global queue_rhyme_round, queued_rhyme_file
    queue_rhyme_round = False
    queued_rhyme_file = None

async def rhyme_round(rhyme_file, persistent_mode=False):
    global rhyme_mode_first_round
    path = os.path.join(WORD_BANK_PATH, rhyme_file)
    with open(path, encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    if not words:
        await send_to_all_channels("⚠️ Rhyme file empty.")
        return
    if persistent_mode:
        if rhyme_mode_first_round:
            await send_to_all_channels("🎯 Dropping rhymes!")
            rhyme_mode_first_round = False
        else:
            await send_to_all_channels("**More rhymes loading:**")
    else:
        await send_to_all_channels("**🎯 Dropping rhymes!**")
    await asyncio.sleep(2)
    interval = round_duration / max(words_per_round, 1)
    for _ in range(min(words_per_round, len(words))):
        await send_to_all_channels(f"🔸{random.choice(words)}🔸")
        await asyncio.sleep(interval)
    if not persistent_mode:
        await send_to_all_channels("🎤 Rhyme round done! Back to normal.")

async def word_round():
    global word_type, used_words, queue_rhyme_round, queued_rhyme_file
    global queue_persistent_rhyme_mode, persistent_rhyme_files_used, rhyme_mode_first_round
    global queue_twister_round
    if stop_signal.is_set(): return
    if queue_twister_round:
        queue_twister_round = False
        await twister_round()
        return
    if queue_persistent_rhyme_mode:
        rhyme_files = [f for f in os.listdir(WORD_BANK_PATH) if f.startswith("rhymes") and f.endswith(".txt")]
        files_left = [f for f in rhyme_files if f not in persistent_rhyme_files_used]
        if not files_left:
            persistent_rhyme_files_used.clear()
            files_left = rhyme_files
        chosen = random.choice(files_left)
        persistent_rhyme_files_used.add(chosen)
        await rhyme_round(chosen, True)
        return
    if queue_rhyme_round and queued_rhyme_file:
        await rhyme_round(queued_rhyme_file, False)
        clear_rhyme_queue()
        return
    words = load_word_list(word_type) if word_type else load_random_words()
    words = [w for w in words if w not in used_words]
    if not words:
        used_words.clear()
        words = load_word_list(word_type) if word_type else load_random_words()
        words = [w for w in words if w not in used_words]
    if not words:
        await send_to_all_channels("No words to drop.")
        return
    await send_to_all_channels("Dropping words, Let's `L I F T` :man_lifting_weights:")
    interval = round_duration / max(words_per_round, 1)
    for _ in range(words_per_round):
        if stop_signal.is_set(): return
        word = random.choice(words)
        used_words.add(word)
        await send_to_all_channels(f"🔹{word}🔹")
        await asyncio.sleep(interval)
    await send_to_all_channels("**:hotsprings: Sheesh! 🔁 Pass the mic!**")
    await asyncio.sleep(5)

async def word_drop_loop():
    global active_session
    while active_session:
        if stop_signal.is_set():
            await asyncio.sleep(1)
        else:
            await word_round()

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(msg):
    global word_type, active_session, stop_signal, used_words, current_task
    global words_per_round, round_duration
    global queue_rhyme_round, queued_rhyme_file
    global queue_persistent_rhyme_mode, persistent_rhyme_files_used, rhyme_mode_first_round
    global queue_twister_round

    if msg.author == client.user: return
    content = msg.content.lower()

    if msg.channel.id not in TARGET_CHANNEL_IDS: return

    if content.startswith("+start"):
        if active_session:
            await msg.channel.send("Already running.")
            return
        active_session = True
        stop_signal.clear()
        used_words.clear()
        clear_rhyme_queue()
        queue_persistent_rhyme_mode = False
        persistent_rhyme_files_used.clear()
        rhyme_mode_first_round = True
        word_type = None
        queue_twister_round = False
        await msg.channel.send("**🎤 Starting word drop in... `3`**")
        await asyncio.sleep(1)
        await msg.channel.send("**🎤 Starting in... `2`**")
        await asyncio.sleep(1)
        await msg.channel.send("**🎤 Starting in... `1`**")
        await asyncio.sleep(1)
        await msg.channel.send("**🎤 GOO!!**")
        current_task = asyncio.create_task(word_drop_loop())

    elif content.startswith("+stop"):
        if not active_session:
            await msg.channel.send("Not active.")
            return
        active_session = False
        stop_signal.set()
        clear_rhyme_queue()
        queue_persistent_rhyme_mode = False
        persistent_rhyme_files_used.clear()
        rhyme_mode_first_round = True
        queue_twister_round = False
        if current_task:
            current_task.cancel()
            try: await current_task
            except: pass
            current_task = None
        await msg.channel.send("🛑 Stopped word drop.")

    elif content.startswith("+reset"):
        word_type = None
        clear_rhyme_queue()
        stop_signal.clear()
        used_words.clear()
        queue_persistent_rhyme_mode = False
        persistent_rhyme_files_used.clear()
        rhyme_mode_first_round = True
        queue_twister_round = False
        await msg.channel.send("_♻️ Reset done._")

    elif content.startswith("+twisters"):
        queue_twister_round = True
        await msg.channel.send("👅 Twister round queued!")

    elif content.startswith("+rhymes"):
        rhyme_files = [f for f in os.listdir(WORD_BANK_PATH) if f.startswith("rhymes") and f.endswith(".txt")]
        if not rhyme_files:
            await msg.channel.send("No rhyme files found.")
            return
        queued_rhyme_file = random.choice(rhyme_files)
        queue_rhyme_round = True
        await msg.channel.send("🎯 Rhyme round queued.")

    elif content.startswith("+rhyme mode"):
        queue_persistent_rhyme_mode = True
        persistent_rhyme_files_used.clear()
        await msg.channel.send("🎯 Persistent Rhyme Mode starting.")

    elif content.startswith("+wordcount"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            words_per_round = int(parts[1])
            await msg.channel.send(f"✅ Words per round set to {words_per_round}.")

    elif content.startswith("+wordtime"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            round_duration = int(parts[1])
            await msg.channel.send(f"✅ Round time set to {round_duration}s.")

    elif content.startswith("+syllables"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            word_type = f\"syllables {parts[1]}\"
            await msg.channel.send(f\"Loading syllables {parts[1]} next round...\")

    elif content.startswith("+nouns"):
        word_type = \"nouns\"
        await msg.channel.send(\"Nouns loading next.\")

    elif content.startswith("+verbs"):
        word_type = \"verbs\"
        await msg.channel.send(\"Verbs loading next.\")

    elif content.startswith("+adjectives"):
        word_type = \"adjectives\"
        await msg.channel.send(\"Adjectives loading next.\")

    elif content.startswith("+adverbs"):
        word_type = \"adverbs\"
        await msg.channel.send(\"Adverbs loading next.\")

    elif content.startswith("+prepositions"):
        word_type = \"prepositions\"
        await msg.channel.send(\"Prepositions loading next.\")

    elif content.startswith("+conjunctions"):
        word_type = \"conjunctions\"
        await msg.channel.send(\"Conjunctions loading next.\")

client.run(TOKEN)
