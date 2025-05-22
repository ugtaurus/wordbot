from keep_alive import keep_alive
keep_alive()
import os
import discord
import asyncio
import random

TOKEN = os.getenv("TOKEN")

# ---------- SETTINGS ---------- #
TARGET_CHANNEL_ID = 1374368615138328656  # Replace with your channel ID
DEFAULT_WORDS_PER_ROUND = 5
DEFAULT_ROUND_DURATION = 30
TWISTER_COOLDOWN = 300  # 5 minutes cooldown between twisters

WORD_BANK_PATH = "wordbanks"

# ---------- GLOBALS ---------- #
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

word_type = None
active_session = False
target_channel = None

twister_mode = False
word_lists = {}

stop_signal = asyncio.Event()

words_per_round = DEFAULT_WORDS_PER_ROUND
round_duration = DEFAULT_ROUND_DURATION

# Track used words for cycling without repetition
used_words = []

# ---------- UTILS ---------- #
def load_word_list(word_type):
    if word_type in word_lists:
        return word_lists[word_type]

    file_path = os.path.join(WORD_BANK_PATH, f"{word_type}.txt")
    if not os.path.isfile(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    word_lists[word_type] = words
    return words

def load_all_words():
    all_words = []
    for file in os.listdir(WORD_BANK_PATH):
        if file.endswith(".txt") and file != "twisters.txt":
            all_words.extend(load_word_list(file[:-4]))
    return all_words

def get_next_words(words, count):
    """
    Return 'count' words from words list, cycling through without repetition.
    Resets used_words when all words have been used.
    """
    global used_words
    available = [w for w in words if w not in used_words]

    if len(available) < count:
        # Reset if not enough available
        used_words = []
        available = words.copy()

    chosen = random.sample(available, count)
    used_words.extend(chosen)
    return chosen

# ---------- WORD ROUND ---------- #
async def word_round():
    global word_type, target_channel, twister_mode, active_session

    if twister_mode:
        # Twister mode should not get here, handled separately
        return

    words = load_word_list(word_type) if word_type else load_all_words()
    if not words:
        await target_channel.send("No words found.")
        return

    words_dropped = 0
    start_time = asyncio.get_event_loop().time()
    interval = round_duration / max(words_per_round, 1)

    await target_channel.send("Dropping words, _Lets L I F T⬇️_")

    while words_dropped < words_per_round and (asyncio.get_event_loop().time() - start_time < round_duration):
        if stop_signal.is_set():
            # Interrupted (e.g. twister mode)
            return
        # Pick next word(s) without repetition
        next_words = get_next_words(words, 1)
        word = next_words[0]
        await target_channel.send(f"🔹{word}🔹")
        words_dropped += 1
        await asyncio.sleep(interval)

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
    global word_type, active_session, target_channel, twister_mode
    global words_per_round, round_duration, stop_signal, used_words

    if message.author == client.user:
        return

    content = message.content.lower()

    if content.startswith("+start") and not active_session:
        active_session = True
        stop_signal.clear()
        await message.channel.send("🎤 Starting word drop session...")
        while active_session:
            await word_round()

    elif content.startswith("+stop"):
        if active_session:
            active_session = False
            stop_signal.set()
            used_words = []
            await message.channel.send("🛑 Word drop session force-stopped.")
        else:
            await message.channel.send("No active session to stop.")

    elif content.startswith("+nouns"):
        word_type = "nouns"
        used_words = []
        await message.channel.send("Loading **nouns** in next round.")

    elif content.startswith("+verbs"):
        word_type = "verbs"
        used_words = []
        await message.channel.send("Loading **verbs** in next round.")

    elif content.startswith("+adjectives"):
        word_type = "adjectives"
        used_words = []
        await message.channel.send("Loading **adjectives** in next round.")

    elif content.startswith("+adverbs"):
        word_type = "adverbs"
        used_words = []
        await message.channel.send("Loading **adverbs** in next round.")

    elif content.startswith("+prepositions"):
        word_type = "prepositions"
        used_words = []
        await message.channel.send("Loading **prepositions** in next round.")

    elif content.startswith("+conjunctions"):
        word_type = "conjunctions"
        used_words = []
        await message.channel.send("Loading **conjunctions** in next round.")

    elif content.startswith("+twisters"):
        if not active_session:
            await message.channel.send("Start a session first using `+start`.")
            return

        stop_signal.set()  # Pause current word round
        twister_mode = True
        await message.channel.send("🎤 Tongue Twister mode activated! Intermission starts now... 🔄")

        twisters = load_word_list("twisters")
        if len(twisters) < 2:
            await message.channel.send("Not enough tongue twisters in the list.")
            twister_mode = False
            stop_signal.clear()
            return

        twister1, twister2 = random.sample(twisters, 2)

        await target_channel.send(f"**{twister1}**")
        await asyncio.sleep(TWISTER_COOLDOWN)  # 5 minutes cooldown
        await target_channel.send(f"**{twister2}**")

        await asyncio.sleep(2)  # small buffer
        twister_mode = False
        stop_signal.clear()  # Resume original word round
        await message.channel.send("🎤 Back to word drops! Picking up where we left off.")

    elif content.startswith("+reset"):
        twister_mode = False
        stop_signal.clear()
        used_words = []
        await message.channel.send("Words reset :recycle:")
        if active_session:
            await word_round()

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

# ---------- KEEP ALIVE ---------- #
keep_alive()

# ---------- RUN ---------- #
client.run(TOKEN)
