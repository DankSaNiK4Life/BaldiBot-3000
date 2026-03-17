import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

from discord_commands import bot
 
if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_BOT_TOKEN")) # Starts the bot 

