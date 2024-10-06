import os
from dotenv import load_dotenv
from bot.Bot import Bot
import random

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# client = discord.Client(intents=discord.Intents.default())
GUILD = os.getenv('DISCORD_GUILD')

bot = Bot()

bot.run(TOKEN)