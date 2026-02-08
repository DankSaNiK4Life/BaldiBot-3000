from platform import system as get_os_name
import discord
import os
from discord.ext import commands, voice_recv
import asyncio
from elevenlabs import save
import json
from config import Config as cfg
from bot_utils import get_real_name
from voice_chat import start_listening, DummySink
from openai_chat import chat_with_gpt
import requests

# ----------------------- INITIALIZATION ----------------------- #

# Initializing the Discord bot
intents = discord.Intents.default() 
intents.messages = True
intents.voice_states = True
intents.message_content = True 
prefixes = ["Baldi ", "baldi ", "hey baldi ", "hey Baldi "]     # List of prefixes the bot will respond to
bot = commands.Bot(command_prefix=prefixes, intents=intents)    # Creating the bot with permissions

# --------------------------------------------------------- #
# --------------- DISCORD EVENTS & COMMANDS --------------- #
# --------------------------------------------------------- #

# On_ready event - This is called when the bot has fully loaded
@bot.event
async def on_ready():
    print("\n-------------------------")
    print("Baldi is ready to teach!")
    print("-------------------------\n")

    # Load chat history from file if it exists
    if os.path.exists(cfg.BACKUP_JSON_FILE):
        with open(cfg.BACKUP_JSON_FILE, "r") as file:
            try:
                cfg.chat_history = json.load(file)  # Load JSON data into cfg.chat_history list
                print("--- Chat history was loaded. ---\n")
            except json.JSONDecodeError:
                print("--- Chat history file is empty or corrupted. Starting fresh. ---\n")
    else:
        print("--- JSON file does not exist. Will create a new one on the first message ---\n")

    # This adds the system message to the chat history on start
    cfg.chat_history.remove(cfg.chat_history[0])
    cfg.chat_history.insert(0, cfg.FIRST_SYSTEM_MESSAGE)

def send_to_twitch(reply_text):
    if not cfg.STREAMERBOT_WEBHOOK_URL:
        print("Streamer.bot webhook URL is not set. Cannot send message to Twitch.")
        return

    payload = {
        "gpt_response": reply_text
    }

    try:
        response = requests.post(cfg.STREAMERBOT_WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            print("Message sent to Twitch successfully.")
        else:
            print(f"Failed to send message to Twitch. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred while sending message to Twitch: {e}")

# On_message event - This lets the bot see what is being said in any chat in the server 
@bot.event
async def on_message(message):
        # Dont listen to its own messages
        if message.author == bot.user:
            return 

        username = str(message.author)
        real_name = get_real_name(username)
        user_message = message.content.lower()
        channel = str(message.channel)

        # Define a dictionary mapping keywords to their corresponding replies
        keyword_responses = {
            "hope": "Hope mentioned.... day ruined :(",
            "ishaq": "I hate that guy smh",
            "arma": "its time you lose some frames!",
            "bee ": ""
        }
        
        # Iterate over the dictionary and check if any keyword is in the user_message
        for keyword, response in keyword_responses.items():
            if keyword in user_message:
                if keyword == "bee ":
                    await message.reply(file=discord.File("images/bee_movie_script.jpg"))
                else:
                    await message.reply(response)
                break  # Stop after the first match

        # This is used to grab Streamer.bot's messages and use them to get chatgpt replies
        if channel == "streamerbot-to-baldibot":
            streamerbot_msg = user_message.split(' ', 1)[1]
            streamerbot_user = user_message.split(' ', 1)[0]
            print("Username: " + streamerbot_user + " " + "Message: " + streamerbot_msg)

            gpt_response = await chat_with_gpt(streamerbot_msg, streamerbot_user)
            send_to_twitch(gpt_response)
        # Check if the bot is mentioned
        elif  bot.user in message.mentions: 
            print("Username: " + username)
            print("Real name: " + real_name)
            await message.reply(await chat_with_gpt(user_message, real_name))

        

        await bot.process_commands(message)  # Allows commands to still work

# Join command - This makes the bot connect to the channel the user is in
@bot.command()
async def join(ctx):

    if (ctx.author.voice):
        channel = ctx.message.author.voice.channel
        
        if discord.utils.get(bot.voice_clients, guild=ctx.guild):
            await ctx.send("I'm already in a voice channel idiot!")
            print("The bot is already in a channel")
            return
        
        cfg.voice_client = await channel.connect(cls=voice_recv.VoiceRecvClient)
        print("The bot has joined the channel")

        cfg.voice_client.listen(DummySink())

        # Starts listening to the user as soon as it joins
        #await start(ctx)
    else:
        await ctx.send("You are not in a voice channel buddy!")
        print("The user is not in a channel")

# Stop command - command used to invoke sub commands
@bot.group(name="stop", invoke_without_command=True)
async def stop(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Stop what?")

# Listening sub-command - This stops the bot from listening 
@stop.command()
async def listening(ctx):
    vc = ctx.voice_client
    if vc and vc.is_listening():
        vc.stop_listening()
        vc.listen(DummySink())
        await ctx.send("I have stopped listening.")
        print("The bot has stopped listening.")
    else:
        await ctx.send("I am not currently listening.")
        print("The bot is not listening.")
 
# Playing sub-command - Makes the bot stop playing a audio file
@stop.command(aliases=["singing"])
async def playing(ctx): 
    vc = ctx.voice_client
    if vc.is_playing():
        vc.stop_playing()
        await ctx.send("I have stopped talking.")
        print("The bot has stopped talking.")
    else:
        await ctx.send("I am not playing anything.")
        print("The bot is not playing anything")

# Listen command - command used to invoke sub commands
@bot.group(name="listen", invoke_without_command=True)
async def listen(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Listen to who?")
        return

# All sub-command - Makes the bot listen to everyone in the voice chat
@listen.command()
async def all(ctx):
    await start_listening(ctx, True)

# To sub-command - Makes the bot listen to the user that was mentioned 
@listen.command()
async def to(ctx, user: str):
    if not ctx.message.mentions:
        await ctx.send("You must mention a user to listen to!")
        return

    await start_listening(ctx, False)

# Say command - Makes the bot say what the user types
@bot.command()
async def say(ctx):
    vc = ctx.voice_client
    if not vc:
        await ctx.send("I am not in a voice channel")
        return
    
    # Extract the text to say (remove the command prefix)
    text = ctx.message.content[len(ctx.prefix) + len("say"):].strip()
    if not text:
        await ctx.send("Please provide some text for me to say!")
        return

    # Generate audio with ElevenLabs
    try:
        audio = await cfg.eleven_client.generate(
            text=text,
            voice=cfg.ELEVENLABS_VOICE,
            model="eleven_multilingual_v2"
        )

        out = b''
        async for value in audio:
            out += value

        # Save the audio to a file
        save(out, "say.mp3")

        # Wait a moment to ensure the audio file is ready
        await asyncio.sleep(1)

        # Play the audio in the voice channel
        if not vc.is_playing():
            vc.play(discord.FFmpegPCMAudio(executable="C:/ffmpeg/bin/ffmpeg.exe", source="say.mp3"))
            print(f"Saying: {text}")
        else:
            await ctx.send("I am already playing something. Please wait!")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        print(f"Error in say command: {e}")

# Sing command - plays one of the mp3 files in "./songs"
@bot.command()
async def sing(ctx):
    vc = ctx.voice_client
    if not vc:
        await ctx.send("I am not in a voice channel")
        return
    
    # Extract the text to say (remove the command prefix)
    text = ctx.message.content[len(ctx.prefix) + len("sing"):].strip()
    if not text:
        await ctx.send("Please provide some text so I know what to sing!")
        return

    # Detect if the bot is on Windows or Linux
    is_windows = get_os_name() == "Windows"
    # Use the correct executable for each environment
    ffmpeg_exe = "ffmpeg/bin/ffmpeg.exe" if is_windows else "ffmpeg"

    if text == "thick of it":
        # Play the song in the voice channel
        if not vc.is_playing():
            vc.play(discord.FFmpegPCMAudio(executable=ffmpeg_exe, source="songs/Baldi_Singing_ThickOfIt.mp3"))
        else:
            await ctx.send("I am already playing something. Please wait!")
    elif text == "like a prayer":
        # Play the song in the voice channel
        if not vc.is_playing():
            vc.play(discord.FFmpegPCMAudio(executable=ffmpeg_exe, source="songs/Baldi_Singing_LikeAPrayer.mp3"))
        else:
            await ctx.send("I am already playing something. Please wait!")
    else:
        await ctx.send("I dont know how to sing that one yet :(")

# Set command - command used to invoke sub commands
@bot.group(name="set", invoke_without_command=True)
async def set(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Set what?")
        return
    
# Context sub-command - Sets the context message for the AI
@set.command()
async def context(ctx):
     
    new_message = ctx.message.content[len(ctx.prefix) + len("set context"):].strip()

    if (new_message.lower() == "default"):
        new_message = cfg.DEFAULT_CONTEXT_MESSAGE

    cfg.FIRST_SYSTEM_MESSAGE["content"] = cfg.FIRST_SYSTEM_MESSAGE["content"].replace(
        f"Context: {cfg.CONTEXT_MESSAGE}",
        f"Context: {new_message}"
        )
    
    cfg.CONTEXT_MESSAGE = new_message

    cfg.chat_history.remove(cfg.chat_history[0])
    cfg.chat_history.insert(0, cfg.FIRST_SYSTEM_MESSAGE)

    print(f"New context message has been set to: {cfg.CONTEXT_MESSAGE}")
    await ctx.send(f"Context message has been set!")

# Show command - command used to invoke sub commands
@bot.group(name="show", invoke_without_command=True)
async def show(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Show what?")
        return

# Last sub-command - Sends the last message of both user and bot
@show.command()
async def last(ctx):
    await ctx.send(f"User said:  {cfg.last_user_message}")
    await ctx.send(f"Baldi said:  {cfg.last_bot_message}")

# Context sub-command - Sends the context message to the user
@show.command()
async def context(ctx):
    await ctx.send(f"Context: {cfg.CONTEXT_MESSAGE}")

# Leave command - Leaves the voice chat
@bot.command()
async def leave(ctx):
    if (ctx.voice_client):
        await ctx.guild.voice_client.disconnect()
        await ctx.send("Seeya later kid!")
        print("The bot has left the channel")
    else:
        await ctx.send("I'm not in a voice channel kid!")
        print("The bot is not in a channel")

# Die Command - Closes the bot
@bot.command()
async def die(ctx):
    #ctx.cfg.voice_client.stop()
    await ctx.bot.close()