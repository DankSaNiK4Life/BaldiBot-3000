from platform import system as get_os_name
import random
import discord
import os
from discord.ext import commands, voice_recv
import asyncio
from elevenlabs import save
import json
from config import Config as cfg
from bot_utils import get_real_name, get_random_sound, start_http_server
from voice_chat import start_listening, DummySink
from openai_chat import chat_with_gpt
import requests
import voice_chat
from personalities import Personalities as p
import sys
import logging
import threading

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
    log_channel = bot.get_channel(cfg.LOG_CHANNEL_ID)
    
    # Saves original console 'write' function so we can still print to console while also sending logs to the channel
    original_write = sys.stdout.write

    sys.stdout.write = lambda msg: (
        original_write(msg), # This keeps it in the HypeServ Panel
        bot.loop.create_task(log_channel.send(f"```\n{msg[:1990]}\n```")) if msg.strip() else None
    )
    
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
    cfg.chat_history.insert(0, cfg.DEFAULT_SYSTEM_MESSAGE)

    # Start the HTTP server for serving audio files
    threading.Thread(target=start_http_server, daemon=True).start()
    print("Started HTTP server for audio files")

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
        message_attachments = message.attachments

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
            if "speaker:" in user_message and not "!" in user_message:
                streamerbot_msg = user_message.split(' ', 1)[1]
                print("SPEAKER MESSAGE: " + streamerbot_msg)
                await message.reply("Received speaker message!")
                
                await voice_chat.gen_with_elevenlabs_streaming(streamerbot_msg, cfg.elevenlabs_voice, cfg.elevenlabs_model)
            elif "cheer:" in user_message:
                streamerbot_msg = user_message.split(' ', 1)[1]
                print("CHEER MESSAGE: " + streamerbot_msg)
                await message.reply("Cheer detected!")

                await voice_chat.gen_with_elevenlabs_streaming(streamerbot_msg, cfg.elevenlabs_voice, cfg.elevenlabs_model)
            elif not "speaker:" in user_message:
                streamerbot_msg = user_message.split(' ', 1)[1]
                streamerbot_user = user_message.split(' ', 1)[0]
                print("Username: " + streamerbot_user + " " + "Message: " + streamerbot_msg)

                gpt_response = await chat_with_gpt(streamerbot_msg, streamerbot_user, message_attachments)
            
                if discord.utils.get(bot.voice_clients):
                    await voice_chat.gen_with_elevenlabs_streaming(gpt_response, cfg.elevenlabs_voice, cfg.elevenlabs_model)
            
                cfg.send_to_twitch(gpt_response)
                print("Baldi's reply on Twitch: " + gpt_response)
                await message.reply(gpt_response)
        # Check if the bot is mentioned
        elif  bot.user in message.mentions: 
            print("Username: " + username + " " + "Real name: " + real_name + " " "Message: " + user_message)

            gpt_response = await chat_with_gpt(user_message, real_name, message_attachments)

            await message.reply(gpt_response)

            if discord.utils.get(bot.voice_clients, guild=message.guild):
                await voice_chat.gen_with_elevenlabs_streaming(gpt_response, cfg.elevenlabs_voice, cfg.elevenlabs_model)

        await bot.process_commands(message)  # Allows commands to still work

# Join command - This makes the bot connect to the channel the user is in
@bot.command()
async def join(ctx):
    if (ctx.author.id not in cfg.TRUSTED_USER_IDS):
        await ctx.reply("You are not trusted, you cannot use this command!")
        return

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

        await play_random_sounds() # Start random sounds when the bot joins a channel
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
    if (ctx.author.id not in cfg.TRUSTED_USER_IDS):
        await ctx.reply("You are not trusted, you cannot use this command!")
        return
    
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
    if (ctx.author.id not in cfg.TRUSTED_USER_IDS):
        await ctx.reply("You are not trusted, you cannot use this command!")
        return
    
    vc = ctx.voice_client
    if vc.is_playing():
        vc.stop_playing()
        await ctx.send("I have stopped talking.")
        print("The bot has stopped talking.")
    else:
        await ctx.send("I am not playing anything.")
        print("The bot is not playing anything")

async def stop_random_sounds():
    print("Random sounds disabled.")
    cfg.random_sounds_enabled = False

# Sounds sub-command - Makes the bot stop playing random sounds in the background
@stop.command()
async def sounds(ctx):
    if (ctx.author.id not in cfg.TRUSTED_USER_IDS):
        await ctx.reply("You are not trusted, you cannot use this command!")
        return
    
    await stop_random_sounds()
    await ctx.send("I have stopped playing random sounds in the background.")

async def play_random_sounds():
    cfg.random_sounds_enabled = True
    print("Random sounds enabled.")
    while discord.utils.get(bot.voice_clients) and cfg.random_sounds_enabled:
            await asyncio.sleep(random.randint(cfg.RANDOM_SOUND_INTERVAL[0], cfg.RANDOM_SOUND_INTERVAL[1])) # random interval between 5 minutes and 1 hour
            if not cfg.random_sounds_enabled: break
            if not cfg.voice_client.is_playing():
                random_sound = get_random_sound()  # Start playing random sounds in the background
                cfg.voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=random_sound))
                print("Played Random Sound: " + random_sound)

# sounds command - This makes the bot continue making random sounds in the background
@bot.command()
async def sounds(ctx):
    if (ctx.author.id not in cfg.TRUSTED_USER_IDS):
        await ctx.reply("You are not trusted, you cannot use this command!")
        return
    
    await ctx.send("I have started playing random sounds in the background.")
    await play_random_sounds()

    


# Listen command - command used to invoke sub commands
@bot.group(name="listen", invoke_without_command=True)
async def listen(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("Listen to who?")
        return

# All sub-command - Makes the bot listen to everyone in the voice chat
@listen.command()
async def all(ctx):
    if (ctx.author.id not in cfg.TRUSTED_USER_IDS):
        await ctx.reply("You are not trusted, you cannot use this command!")
        return
    
    await start_listening(ctx, True)

# To sub-command - Makes the bot listen to the user that was mentioned 
@listen.command()
async def to(ctx, user: str):
    if (ctx.author.id not in cfg.TRUSTED_USER_IDS):
        await ctx.reply("You are not trusted, you cannot use this command!")
        return
    
    if not ctx.message.mentions:
        await ctx.send("You must mention a user to listen to!")
        return

    await start_listening(ctx, False)

# Say command - Makes the bot say what the user types
@bot.command()
async def say(ctx):
    if (ctx.author.id not in cfg.TRUSTED_USER_IDS):
        await ctx.reply("You are not trusted, you cannot use this command!")
        return
    
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
        # Play the audio in the voice channel
        if not vc.is_playing():
            await voice_chat.gen_with_elevenlabs_streaming(text, cfg.elevenlabs_voice, cfg.elevenlabs_model)
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
    if (ctx.author.id not in cfg.TRUSTED_USER_IDS):
        await ctx.reply("You are not trusted, you cannot use this command!")
        return
    
    new_message = ctx.message.content[len(ctx.prefix) + len("set context"):].strip()

    if (new_message.lower() == "default"):
        new_message = p.DEFAULT_CONTEXT_MESSAGE

    cfg.DEFAULT_SYSTEM_MESSAGE["content"] = cfg.DEFAULT_SYSTEM_MESSAGE["content"].replace(
        f"Context: {p.CONTEXT_MESSAGE}",
        f"Context: {new_message}"
        )
    
    cfg.CONTEXT_MESSAGE = new_message

    cfg.chat_history.remove(cfg.chat_history[0])
    cfg.chat_history.insert(0, cfg.DEFAULT_SYSTEM_MESSAGE)

    print(f"New context message has been set to: {cfg.CONTEXT_MESSAGE}")
    await ctx.send(f"Context message has been set!")

# Personality sub-command - Sets the personality for the AI (different system messages)
@set.command()
async def personality(ctx):
    if (ctx.author.id not in cfg.TRUSTED_USER_IDS):
        await ctx.reply("You are not trusted, you cannot use this command!")
        return
    
    new_message = ctx.message.content[len(ctx.prefix) + len("set personality"):].strip()

    if new_message.lower() == "sane baldi":
        cfg.DEFAULT_SYSTEM_MESSAGE = p.SANE_BALDIS_FIRST_SYSTEM_MESSAGE
        cfg.BACKUP_JSON_FILE = "backups/SaneBaldiChatHistoryJsonBackup.json"
        cfg.elevenlabs_voice = "vrkuGKtvocSoZvsaAeUM"
        cfg.elevenlabs_model = "eleven_v3"
        p.CURRENT_PERSONALITY = "sane baldi"
    elif new_message.lower() == "baldi":
        cfg.DEFAULT_SYSTEM_MESSAGE = p.BALDIS_FIRST_SYSTEM_MESSAGE
        cfg.BACKUP_JSON_FILE = "backups/BaldiHistoryJsonBackup.json"
        cfg.elevenlabs_voice = "CGOMbDUL52Yuc7oiDIm8"
        cfg.elevenlabs_model = "eleven_multilingual_v2"
        p.CURRENT_PERSONALITY = "baldi"
    else:
        await ctx.send("Unknown personality! Available personalities are: 'Baldi' and 'Sane Baldi'")
        return
        

    cfg.chat_history.remove(cfg.chat_history[0])
    cfg.chat_history.insert(0, cfg.DEFAULT_SYSTEM_MESSAGE)

    print(f"New personality has been set to: {new_message}")
    print(f"New voice has been set to: {cfg.elevenlabs_voice}")
    print(f"New model has been set to: {cfg.elevenlabs_model}")
    await ctx.send(f"Personality has been set!")

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
    await ctx.send(f"Context: {p.CONTEXT_MESSAGE}")

# Personality sub-command - Sends the current personality to the user
@show.command()
async def personality(ctx):
    await ctx.send(f"Current Personality: {p.CURRENT_PERSONALITY}")

# Commands sub-command - Lists all commands
@show.command()
async def commands(ctx):
    commands_message = f'''**Available commands for BaldiBot 3000: **
`@BaldiBot 3000 - Allows you to talk to the bot and get responses (Will play audio if in a vc)
baldi show - used for sub commands:
    last - Sends the last message of both user and bot
    context - Sends the context message
    personality - Sends the current personality name
    commands - Sends this exact message!`

**For Trusted Members:**
`baldi join - Makes bot join voice channel that you are currently in
baldi stop - used for sub commands:
    listening - Stops the bot from listening to anyone 
    playing (or singing) - Stops the bot from playing any audio files
    sounds - Stops bot from playing random sounds every 5 - 60 minutes
baldi listen - used for sub commands:
    all - Makes bot listen to everyone in the voice chat (Will combine peoples sentences together)
    to - Makes bot listen to a specific person (More stable option)
baldi say - Makes bot generate anything you want using elevenlabs
baldi sing - Makes bot play available audio files:
    thick of it
    like a prayer
baldi set - used for sub commands:
    context - Used to tell the bot what you and or they are doing right now
    personality - Used to set how the bot will act (and can change voice):
        baldi
        sane baldi
baldi leave - Makes bot leave the voice channel
baldi sounds - This makes the bot continue making random sounds in the background`

**For Owner ONLY:**
`baldi die - turns off the bot`'''
    
    await ctx.send(commands_message)

# Leave command - Leaves the voice chat
@bot.command()
async def leave(ctx):
    if (ctx.author.id not in cfg.TRUSTED_USER_IDS):
        await ctx.reply("You are not trusted, you cannot use this command!")
        return
    
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
    if (ctx.author.id != cfg.OWNER_ID):
        await ctx.reply("You are not my owner, you cannot use this command!")
        return
    
    #ctx.cfg.voice_client.stop()
    await ctx.bot.close()

