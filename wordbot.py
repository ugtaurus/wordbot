import discord
import asyncio
import random
import os

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Word file paths
WORD_FILES = {
    "adjectives": "adjectives.txt",
    "adverbs": "adverbs.txt",
    "verbs": "verbs.txt",
    "prepositions": "prepositions.txt",
    "nouns": "nouns.txt",
    "conjunctions": "conjunctions.txt"
}

SYLLABLE_FILES = {i: f"syllables {i}.txt" for i in range(1, 13)}
TWISTERS_FILE = "Twisters.txt"

# Load word lists
def load_word_list(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    return []

word_lists = {name: load_word_list(path) for name, path in WORD_FILES.items()}
syllable_word_lists = {num: load_word_list(path) for num, path in SYLLABLE_FILES.items()}
twisters = load_word_list(TWISTERS_FILE)

# Runtime variables
word_drop_active = False
syllable_filter = None
wordtype_filter = []
twister_mode = False
current_twister_index = 0

async def drop_words(channel):
    global word_drop_active, syllable_filter, wordtype_filter, twister_mode
    while word_drop_active:
        if twister_mode:
            await channel.send("**\ud83c\udfa4 Starting Twister mode with automatic repeat!**")
            await asyncio.sleep(1)
            if current_twister_index < len(twisters):
                await channel.send(f"**Here's a twister:**\n**{twisters[current_twister_index]}**")
                await asyncio.sleep(60)
                current_twister_index += 1
                if current_twister_index < len(twisters):
                    await channel.send(f"**Here's another twister:**\n**{twisters[current_twister_index]}**")
                    await asyncio.sleep(60)
                else:
                    current_twister_index = 0
            twister_mode = False
            await channel.send("\ud83c\udfa4 Resuming word drop session...")

        await channel.send("Dropping words, Lets L I F T\u2b07\ufe0f")
        words_to_drop = []

        if syllable_filter:
            words_to_drop = syllable_word_lists.get(syllable_filter, [])
        elif wordtype_filter:
            for wt in wordtype_filter:
                words_to_drop += word_lists.get(wt, [])
        else:
            words_to_drop += syllable_word_lists[1] + syllable_word_lists[3]

        if not words_to_drop:
            await channel.send("No words found to drop.")
        else:
            selected_words = random.sample(words_to_drop, min(5, len(words_to_drop)))
            for word in selected_words:
                await channel.send(f"\ud83d\udd39{word}\ud83d\udd39")
            await asyncio.sleep(3)
            await channel.send("\ud83d\udd25 Sheesh, fire!! Time to pass the Metal! \ud83d\udd01")

        await asyncio.sleep(5)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    global word_drop_active, syllable_filter, wordtype_filter, twister_mode, current_twister_index
    if message.author == client.user:
        return

    content = message.content.lower()

    if content.startswith("+start"):
        word_drop_active = True
        await message.channel.send("\ud83c\udfa4 Starting word drop session...")
        await drop_words(message.channel)

    elif content.startswith("+stop"):
        word_drop_active = False
        await message.channel.send("\ud83d\udea9 Word drop session force-stopped.")

    elif content.startswith("+twisters"):
        if not word_drop_active:
            word_drop_active = True
            twister_mode = True
            current_twister_index = 0
            await drop_words(message.channel)
        else:
            twister_mode = True
            current_twister_index = 0

    elif content.startswith("+reset"):
        syllable_filter = None
        wordtype_filter = []
        await message.channel.send("Words reset \u267b\ufe0f")

    elif content.startswith("+syllables"):
        try:
            num = int(content.split()[1])
            if num in syllable_word_lists:
                syllable_filter = num
                await message.channel.send(f"Loading words with {num} syllable(s) in next round...")
            else:
                await message.channel.send("Invalid syllable count.")
        except:
            await message.channel.send("Use format: +syllables <number>")

    elif content.startswith("+filter"):
        parts = content.split()
        wordtype_filter = [pt for pt in parts[1:] if pt in word_lists]
        await message.channel.send(f"Word filters updated: {', '.join(wordtype_filter)}")

TOKEN = os.getenv("TOKEN")
client.run(TOKEN)
