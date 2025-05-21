from keep_alive import keep_alive
keep_alive()
import os
import discord
import asyncio
import random
from dotenv import load_dotenv
from keep_alive import keep_alive  # make sure keep_alive.py is in the same folder

# Load token from .env file
load_dotenv()
TOKEN = os.getenv("TOKEN")

# ---------- SETTINGS ---------- #
TARGET_CHANNEL_ID = 1374368615138328656  # Replace with your target channel ID

WORDS_PER_ROUND = 8        # Default number of words per round
ROUND_DURATION = 60        # Default duration of each round in seconds
TWISTER_COOLDOWN = 600     # Cooldown after sending a twister (in seconds)

WORD_BANK_PATH = "wordbanks"  # Folder where your word files are stored

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
    word_lists[word_type] = words
    return words

def load_all_words():
    all_words = []
    for file in os.listdir(WORD_BANK_PATH):
        if file.endswith(".txt") and file != "twisters.txt":
            all_words.extend(load_word_list(file[:-4]))
    return all_words

# ---------- WORD ROUND ---------- #
async def word_round():
    global word_type, target_channel, twister_mode, active_session

    if twister_mode:
        twisters = load_word_list("twisters")
        if not twisters:
            await target_channel.send("No tongue twisters found.")
            twister_mode = False
            return
        twister = random.choice(twisters)
        await target_channel.send(f"**{twister}**")
        await asyncio.sleep(TWISTER_COOLDOWN)
        twister_mode = False
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
            return
        word = random.choice(words)
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
    global words_per_round, round_duration, stop_signal

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
            await message.channel.send("🛑 Word drop session force-stopped.")
        else:
            await message.channel.send("No active session to stop.")

    elif content.startswith("+nouns"):
        word_type = "nouns"
        await message.channel.send("Switched to **nouns**.")

    elif content.startswith("+verbs"):
        word_type = "verbs"
        await message.channel.send("Switched to **verbs**.")

    elif content.startswith("+adjectives"):
        word_type = "adjectives"
        await message.channel.send("Switched to **adjectives**.")

    elif content.startswith("+adverbs"):
        word_type = "adverbs"
        await message.channel.send("Switched to **adverbs**.")

    elif content.startswith("+prepositions"):
        word_type = "prepositions"
        await message.channel.send("Switched to **prepositions**.")

    elif content.startswith("+conjunctions"):
        word_type = "conjunctions"
        await message.channel.send("Switched to **conjunctions**.")

    elif content.startswith("+twisters"):
        twister_mode = True
        stop_signal.set()
        await message.channel.send("Here comes a tongue twister... 🔄")
        await word_round()

    elif content.startswith("+reset"):
        twister_mode = False
        stop_signal.clear()
        await message.channel.send("Twister mode cancelled. Back to word drops.")
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