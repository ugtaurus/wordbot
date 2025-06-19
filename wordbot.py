from keep_alive import keep_alive
keep_alive()

import os
import discord
import asyncio
import random

TOKEN = os.getenv("TOKEN")

# ---------- SETTINGS ---------- #
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

sessions = {}  # channel_id: dict with session state
word_lists = {}

# ---------- HELPERS ---------- #
async def send_to_channel(channel, msg):
    try:
        await channel.send(msg)
    except Exception as e:
        print(f"Error sending to channel {channel.id}: {e}")

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

# ---------- MAIN LOGIC ---------- #
async def word_round(channel, state):
    if state['stop_signal'].is_set():
        return

    words = load_word_list(state['word_type']) if state['word_type'] else load_random_words()
    words = [w for w in words if w not in state['used_words']]
    if not words:
        state['used_words'].clear()
        words = load_word_list(state['word_type']) if state['word_type'] else load_random_words()
    if not words:
        await send_to_channel(channel, "No words to drop.")
        return

    await send_to_channel(channel, "Dropping words, Let's `L I F T` :man_lifting_weights:")
    interval = state['round_duration'] / max(state['words_per_round'], 1)

    for _ in range(state['words_per_round']):
        if state['stop_signal'].is_set():
            return
        word = random.choice(words)
        state['used_words'].add(word)
        await send_to_channel(channel, f"🔹{word}🔹")
        await asyncio.sleep(interval)

    await send_to_channel(channel, "**:hotsprings: Sheesh! 🔁 Pass the mic!**")
    await asyncio.sleep(5)

async def word_drop_loop(channel, state):
    while state['active']:
        if state['stop_signal'].is_set():
            await asyncio.sleep(1)
        else:
            await word_round(channel, state)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(msg):
    if msg.author == client.user:
        return

    channel = msg.channel
    cid = channel.id
    content = msg.content.lower()

    if cid not in sessions:
        sessions[cid] = {
            'active': False,
            'stop_signal': asyncio.Event(),
            'used_words': set(),
            'word_type': None,
            'words_per_round': WORDS_PER_ROUND,
            'round_duration': ROUND_DURATION,
            'task': None
        }

    state = sessions[cid]

    if content.startswith("+start"):
        if state['active']:
            await send_to_channel(channel, "Already running.")
            return
        state['active'] = True
        state['stop_signal'].clear()
        state['used_words'].clear()
        state['task'] = asyncio.create_task(word_drop_loop(channel, state))
        await send_to_channel(channel, "**🎤 Starting word drop in... `3`**")
        await asyncio.sleep(1)
        await send_to_channel(channel, "**🎤 Starting in... `2`**")
        await asyncio.sleep(1)
        await send_to_channel(channel, "**🎤 Starting in... `1`**")
        await asyncio.sleep(1)
        await send_to_channel(channel, "**🎤 GOO!!**")

    elif content.startswith("+stop"):
        if not state['active']:
            await send_to_channel(channel, "Not active.")
            return
        state['active'] = False
        state['stop_signal'].set()
        if state['task']:
            state['task'].cancel()
            try:
                await state['task']
            except:
                pass
            state['task'] = None
        await send_to_channel(channel, "🛑 Stopped word drop.")

    elif content.startswith("+reset"):
        state['word_type'] = None
        state['stop_signal'].clear()
        state['used_words'].clear()
        await send_to_channel(channel, "_♻️ Reset done._")

    elif content.startswith("+wordcount"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            state['words_per_round'] = int(parts[1])
            await send_to_channel(channel, f"✅ Words per round set to {state['words_per_round']}.")

    elif content.startswith("+wordtime"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            state['round_duration'] = int(parts[1])
            await send_to_channel(channel, f"✅ Round time set to {state['round_duration']}s.")

    elif content.startswith("+syllables"):
        parts = content.split()
        if len(parts) == 2 and parts[1].isdigit():
            state['word_type'] = f"syllables {parts[1]}"
            await send_to_channel(channel, f"Loading syllables {parts[1]} next round...")

    elif content.startswith("+nouns"):
        state['word_type'] = "nouns"
        await send_to_channel(channel, "Nouns loading next.")

    elif content.startswith("+verbs"):
        state['word_type'] = "verbs"
        await send_to_channel(channel, "Verbs loading next.")

    elif content.startswith("+adjectives"):
        state['word_type'] = "adjectives"
        await send_to_channel(channel, "Adjectives loading next.")

    elif content.startswith("+adverbs"):
        state['word_type'] = "adverbs"
        await send_to_channel(channel, "Adverbs loading next.")

    elif content.startswith("+prepositions"):
        state['word_type'] = "prepositions"
        await send_to_channel(channel, "Prepositions loading next.")

    elif content.startswith("+conjunctions"):
        state['word_type'] = "conjunctions"
        await send_to_channel(channel, "Conjunctions loading next.")

client.run(TOKEN)
