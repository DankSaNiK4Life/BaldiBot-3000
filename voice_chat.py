import time, asyncio, discord, logging, io, speech_recognition as sr
from config import Config as cfg
from bot_utils import get_real_name, set_source_visibility, get_source_visibility
from discord.ext import voice_recv
from openai_chat import chat_with_gpt
from obswebsocket import obsws, requests as obs_requests
from obs_websockets import ws

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])

# Specifically silence the voice_recv reader and library noise
logging.getLogger('discord.ext.voice_recv.reader').setLevel(logging.WARNING)
logging.getLogger('discord.ext.voice_recv').setLevel(logging.WARNING) 

# Dummy sink that discards audio data (here for now until I figure out a way to clear audio data properly lol)
class DummySink(voice_recv.AudioSink):
    def write(self, user, data):
        pass  # Discard the audio data
    
    def cleanup(self):
        pass  # No cleanup needed for this dummy sink

    def wants_opus(self):
        return False  # Indicate that this sink does not want Opus-encoded audio

# Wait_for_silence function - This is used to detect when someone has stopped talking for a certain time or if max_duration was reached (this then calls process_response)
async def wait_for_silence(max_duration, silence_timeout, ctx):
    
    while cfg.voice_client.is_listening():
        elapsed_time = time.time() - cfg.start_time
        silence_duration = time.time() - cfg.last_speech_time

        # Stop if max duration is reached OR silence lasts too long
        if elapsed_time >= max_duration:
            print("\nMax duration reached. Stopping recognition.")
            break
        if silence_duration >= silence_timeout:
            print("\nSilence detected. Stopping recognition.")
            break

        await asyncio.sleep(0.2) # Prevent CPU overload

    final_result = " ".join(cfg.all_results).strip()
    print(f"\nFinal result: {final_result}\n")

    cfg.is_waiting_for_silence = False
    await process_response(final_result, ctx)

# Process_response function - This is used to take the user's final response and send it to openai (this then calls text_to_audio_played)
async def process_response(final_result, ctx):

    if not final_result or final_result == " ":
        #final_result = "*stays silent*"
        #print(f"\nFinal result changed to: {final_result}\n")
        return  # Don't process empty messages

    cfg.voice_client.stop_listening()
    print("Stopped listening to speech")

    # This checks if the bot is listening to a specific user or everyone and then inputs the correct name
    if cfg.listen_to_name:
        real_name = get_real_name(cfg.listen_to_name)
        cfg.listen_to_name = None
    else: real_name = "Unknown_User"

    openai_answer = await chat_with_gpt(final_result, real_name, image_attachment=None)
    print(f"\nBaldi says: {openai_answer}\n")
    await text_to_audio_played(openai_answer, ctx)  # Play response in voice chat

async def gen_with_elevenlabs_remote(audio_data, input_text, msg_type="normal", username="", bits=""):
    # SAVE the audio to a web-accessible folder on your server
    with open("./sounds/temp_audio.mp3", "wb") as f:
        f.write(audio_data)
    print("Saved new audio file")

    # Used to test getting the filter settings and data from OBS (not needed anymore but might be useful in the future)    
    """
    testresponse = ws.call(obs_requests.GetSourceFilter(
        sourceName=cfg.message_source,
        filterName="Move Value"
    ))
    print(testresponse.datain)
    """

    # This is used if someone gives bits and a message on Twitch
    if msg_type == "cheer":
        print("Cheer message detected.")
        ws.call(obs_requests.SetSourceFilterSettings(
                sourceName="ChatterTTSMelonMessage",
                filterName="Move Value",
                filterSettings={"setting_text": input_text},
                overlay=True
            )
        )

        # This is used to set the username & bits text in OBS (if using OBS for audio playback)
        ws.call(obs_requests.SetInputSettings(inputName="ChatterTTSMelonUsername", inputSettings = {'text': username}))
        ws.call(obs_requests.SetInputSettings(inputName="ChatterTTSMelonBits", inputSettings = {'text': bits + " bits"}))

        set_source_visibility(ws, scene_name="GLOBAL Scene", source_name="ChatterTTSMelon", source_visible=True)
        set_source_visibility(ws, scene_name="GLOBAL Scene", source_name="RemoteAudio", source_visible=True)

    # This is used if someone is the speaker on Twitch
    elif msg_type == "speaker":
        print("Speaker message detected.")
        ws.call(obs_requests.SetSourceFilterSettings(
                sourceName="SpeakerMelonMessage",
                filterName="Move Value",
                filterSettings={"setting_text": input_text},
                overlay=True
            )
        )

        # This is used to set the username text in OBS (if using OBS for audio playback)
        ws.call(obs_requests.SetInputSettings(inputName="SpeakerMelonUsername", inputSettings = {'text': username}))

        set_source_visibility(ws, scene_name="GLOBAL Scene", source_name="SpeakerMelon", source_visible=True)
        set_source_visibility(ws, scene_name="GLOBAL Scene", source_name="RemoteAudio", source_visible=True)

    # This is used for normal messages (e.g. from the user speaking)
    elif msg_type == "normal":
        print("Normal message detected.")
        # Sets "Move Value" filter text to the user's message (this is used to show the user's message in OBS as a text source filter)
        ws.call(obs_requests.SetSourceFilterSettings(
                sourceName=cfg.message_source,
                filterName="Move Value",
                filterSettings={"setting_text": input_text},
                overlay=True
            )
        )

        # This is used to make the AI's image and audio source visible in OBS (if using OBS for audio playback)
        set_source_visibility(ws, scene_name="GLOBAL Scene", source_name=cfg.ai_image_source, source_visible=True)
        set_source_visibility(ws, scene_name="GLOBAL Scene", source_name="RemoteAudio", source_visible=True)

    while get_source_visibility(ws, scene_name="GLOBAL Scene", source_name="RemoteAudio") == True:
        await asyncio.sleep(2)
        print("WAITING FOR VOICE TO END") 

    await asyncio.sleep(2.5) # Waits for the OBS image soure to disable before sending (To prevent two images on screen at once)
    cfg.send_to_streamer_bot(voice_stopped=True)

async def gen_with_elevenlabs_streaming(input_text, voice, model, msg_type="normal", username="", bits=""):
    if (cfg.voice_client is None or not cfg.voice_client.is_connected()) and not cfg.obs_enabled:
         print("Bot is not in a voice channel & OBS is not on. Cannot generate with Elevenlabs")
         return
    
    from discord_commands import play_random_sounds, stop_random_sounds
    await stop_random_sounds() # Stop random sounds while the bot is speaking
    
    response = cfg.eleven_client.text_to_speech.stream(
        voice_id=voice,
        output_format="mp3_22050_32",
        text=input_text,
        model_id=model
    )

    # Collect all chunks into one bytes object
    audio_data = b"".join([chunk for chunk in response if chunk])
    
    # Create a BytesIO object from the collected bytes
    audio_buffer = io.BytesIO(audio_data)
    
    if cfg.voice_client is not None and cfg.voice_client.is_connected(): 
        cfg.voice_client.play(discord.FFmpegPCMAudio(audio_buffer, pipe=True, executable="ffmpeg"))
    
    if cfg.obs_enabled:
        await gen_with_elevenlabs_remote(audio_data, input_text, msg_type, username, bits) # Stream the audio to OBS (if using OBS for audio playback)
    
    #if ws.ws.connected:
    #    print("Connected to OBS WebSocket")
    #    await gen_with_elevenlabs_remote(ws, audio_data, input_text) # Stream the audio to OBS (if using OBS for audio playback)
    #else:
    #    print("Failed to connect to OBS WebSocket. Playing audio directly in Discord.")
    #    cfg.voice_client.play(discord.FFmpegPCMAudio(audio_buffer, pipe=True, executable="ffmpeg"))
    
    print("\n--- ElevenLabs Streaming Generated & Played Audio. ---")
    print(f"Voice used: {voice}")
    print(f"Model used: {model}\n")

    await play_random_sounds() # Start random sounds again after the bot has finished speaking

# Text_to_audio_played function - This is used to generate a mp3 file from openai's reply and then play it
async def text_to_audio_played(input_text, ctx):

    if cfg.voice_client.is_playing(): return

    response_start_time = time.time()
    await gen_with_elevenlabs_streaming(input_text)
    #await gen_with_sovits(input_text, ctx)
    #await gen_with_sovits_streaming(input_text, ctx)

    response_time = time.time() - response_start_time
    print(f"\nResponse time: {int(response_time // 60):02d}:{int(response_time % 60):02d}.{int((response_time % 1) * 1000):03d}\n")


    # POSSIBLY MOVE THIS INTO GEN FUNCTION 
    # Restart speech recognition after audio playback is complete
    while cfg.voice_client.is_playing():
        cfg.voice_client.stop_listening()
        cfg.voice_client.listen(DummySink())
        await asyncio.sleep(0.5)
    from discord_commands import bot
    if cfg.is_listen_to_all: await ctx.invoke(bot.get_command("listen all"))
    else: await ctx.invoke(bot.get_command("listen to"), ctx.author.mention)
    print("Resumed listening to speech.")

# Start_listening function - This is used with the listen sub-commands (all, to)
async def start_listening(ctx, is_listen_all):
    
    cfg.is_listen_to_all = is_listen_all

    # Stop the DummySink if it's active
    cfg.voice_client.stop_listening()

    if not cfg.voice_client:
        await ctx.send("I am not in a voice channel.")
        return
    
    if cfg.voice_client.is_listening():
        await ctx.send("I am already listening!")
        return

    cfg.cb_ctx = ctx
    cfg.start_time = time.time()
    cfg.last_speech_time = time.time()
    cfg.all_results = []

    ''' # Peoples Discord User IDs
    reece = ctx.guild.get_member(205472888755716107)
    bailey = ctx.guild.get_member(838854430111301652)
    taylor = ctx.guild.get_member(872867731580530718)
    userList = [reece, bailey, taylor]

    if not userList:
        print("One or more users to track are not in the voice channel!")
        return
    '''

    if is_listen_all:
        cfg.voice_client.listen(voice_recv.extras.speechrecognition.SpeechRecognitionSink(process_cb=cb, phrase_time_limit=5))
        await ctx.send(f"I am now listening!")
        print("The bot is listening to user")
    else:
        mentioned_user = ctx.message.mentions[0]
        cfg.listen_to_name = mentioned_user.name

        # Check if the mentioned user is in the same voice channel as the bot
        if not mentioned_user.voice or mentioned_user.voice.channel != cfg.voice_client.channel:
            await ctx.send(f"{mentioned_user.display_name} is not in the same voice channel as me!")
            return

        cfg.voice_client.listen(voice_recv.UserFilter(voice_recv.extras.speechrecognition.SpeechRecognitionSink(process_cb=cb, phrase_time_limit=5), mentioned_user))
        await ctx.send(f"Now listening to {mentioned_user.display_name}!")
        print(f"\nThe bot is listening to {mentioned_user.display_name}\n")

# Cb function - This is a callback function that vc.listen() uses to actually recognize and listen to the user (This calls wait_for_silence)
def cb(user: discord.Member, audio: sr.AudioData, third=None):
        #nonlocal all_results, last_speech_time, start_time
            
        user_name = user.display_name if isinstance(user, discord.Member) else "Unknown User"
        recognizer = sr.Recognizer()
        
        try:
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)

            text, confidence = recognizer.recognize_azure(audio, key=cfg.AZURE_TTS_KEY, location=cfg.AZURE_TTS_REGION, profanity="raw")
            print(f"Recognized text from {user_name}: {text}")

            trigger_phrases = {
                "screenshot": ["look at this", "check this out", "see this", "see it", "see my", "screenshot this"],
            }

            # Check if the user said "stop listening"
            if "stop listening" in text.lower():
                from discord_commands import bot, stop
                asyncio.run_coroutine_threadsafe(stop(cfg.cb_ctx), bot.loop)
                return  # Exit the callback to stop further processing

            if any(phrase in text.lower() for phrase in trigger_phrases.get("screenshot", [])):
                print("Screenshot Triggered")
                cfg.is_image_message = True

            if text: # Recognized text
                #all_results.append(f"{user_name}: {text}")
                cfg.all_results.append(text)
                cfg.last_speech_time = time.time() # Reset silence timer
                
        except sr.UnknownValueError:
            #print(f"Did not recognize {user_name if user else 'Unknown User'}'s audio")
            #print(f"Did not recognize {user.display_name}'s audio")
            return
        except sr.RequestError as e:
            print(f"Azure Speech Service error: {e}")
            # Retry after a short delay
            time.sleep(1)
            return

        if not cfg.is_waiting_for_silence:
                    cfg.is_waiting_for_silence = True
                    #all_results.clear()
                    #start_time = time.time()
                    #last_speech_time = time.time()
                    from discord_commands import bot
                    bot.loop.create_task(wait_for_silence(cfg.MAX_DURATION, cfg.SILENCE_TIMEOUT, cfg.cb_ctx))

        # Run silence detection in the background
        #bot.loop.create_task(wait_for_silence(all_results, last_speech_time, start_time, max_duration, silence_timeout, vc))

        #openai_answer = asyncio.run(chat_with_gpt(final_result))
        #print(f"Baldi says: {openai_answer}")
        #bot.loop.create_task(ctx.send(openai_answer))
        #asyncio.run(text_to_audio_played(openai_answer, vc=vc, voice=elevenlabs_voice))
        #return final_result

