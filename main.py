import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

from discord_commands import bot
import psutil
 
if __name__ == "__main__":
    exe_path = "venv/Scripts/gpt_sovits_api.exe"
    exe_name = os.path.basename(exe_path)

    # If the API is not already running then run it
    if not any(exe_name.lower() in p.info['name'].lower() for p in psutil.process_iter(['name']) if p.info['name']):
        os.startfile(exe_path)

    bot.run(os.getenv("DISCORD_BOT_TOKEN")) # Starts the bot 

