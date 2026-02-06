from config import Config as cfg
from bot_utils import get_real_name
from elevenlabs import save
from discord.ext import voice_recv
from openai_chat import chat_with_gpt
import time
import asyncio
import discord
import speech_recognition as sr
from rvc_python.infer import RVCInference
import requests
import aiohttp
from GPT_SoVITS.TTS_infer_pack.TTS import TTS as GPTSoVITSPipeline
from GPT_SoVITS.TTS_infer_pack.TTS import TTS_Config as GPTSoVITSConfig
import json
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])
import wave
import io
import sounddevice as sd
import os

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
        final_result = "*stays silent*"
        print(f"\nFinal result changed to: {final_result}\n")
        #return  # Don't process empty messages

    cfg.voice_client.stop_listening()
    print("Stopped listening to speech")

    # This checks if the bot is listening to a specific user or everyone and then inputs the correct name
    if cfg.listen_to_name:
        real_name = get_real_name(cfg.listen_to_name)
        cfg.listen_to_name = None
    else: real_name = "Unknown_User"

    openai_answer = await chat_with_gpt(final_result, real_name)
    print(f"Baldi says: {openai_answer}")
    await text_to_audio_played(openai_answer, ctx, cfg.ELEVENLABS_VOICE)  # Play response in voice chat

async def gen_with_elevenlabs(input_text, voice):
    audio = await cfg.eleven_client.generate(
        text=input_text,
        voice=voice,
        model="eleven_multilingual_v2"
    )

    out = b''
    async for value in audio:
        out += value

    save(out, "audio.mp3")

    # Wait a moment to ensure audio file is ready
    await asyncio.sleep(1)

    cfg.voice_client.play(discord.FFmpegPCMAudio(executable="C:/ffmpeg/bin/ffmpeg.exe", source="audio.mp3"))

    return print("--- ElevenLabs Generated & Played Audio. ---")

async def gen_with_sovits(input_text, ctx):

    '''config_path = "configs/tts_infer.yaml"

    tts_config = GPTSoVITSConfig(config_path)
    tts_pipeline = GPTSoVITSPipeline(tts_config)

    gpt_model_path = "models/BaldiMelonHeadV2/GPT_weights/BaldiMelonHeadV2-e10.ckpt"
    sovits_model_path = "models/BaldiMelonHeadV2/SoVITS_weights/BaldiMelonHeadV2_e8_s832.pth"
    tts_pipeline.init_t2s_weights(weights_path=gpt_model_path)
    tts_pipeline.init_vits_weights(weights_path=sovits_model_path)'''

    # API configuration
    host = '127.0.0.1'
    port = 9880
    url = f'http://{host}:{port}/tts'

    '''json
    {
        "text": "",                   # str.(required) text to be synthesized
        "text_lang: "",               # str.(required) language of the text to be synthesized
        "ref_audio_path": "",         # str.(required) reference audio path
        "aux_ref_audio_paths": [],    # list.(optional) auxiliary reference audio paths for multi-speaker tone fusion
        "prompt_text": "",            # str.(optional) prompt text for the reference audio
        "prompt_lang": "",            # str.(required) language of the prompt text for the reference audio
        "top_k": 5,                   # int. top k sampling
        "top_p": 1,                   # float. top p sampling
        "temperature": 1,             # float. temperature for sampling
        "text_split_method": "cut0",  # str. text split method, see text_segmentation_method.py for details.
        "batch_size": 1,              # int. batch size for inference
        "batch_threshold": 0.75,      # float. threshold for batch splitting.
        "split_bucket: True,          # bool. whether to split the batch into multiple buckets.
        "speed_factor":1.0,           # float. control the speed of the synthesized audio.
        "streaming_mode": False,      # bool. whether to return a streaming response.
        "seed": -1,                   # int. random seed for reproducibility.
        "parallel_infer": True,       # bool. whether to use parallel inference.
        "repetition_penalty": 1.35    # float. repetition penalty for T2S model.
    }
    '''

    # Parameters for the request
    params = {
        'text': input_text,
        'text_lang': 'en',
        'ref_audio_path': 'balditest.wav',
        'prompt_lang': 'en',
        'prompt_text': 'Oh, Hi. Welcome to my school house!',
        'text_split_method': 'cut0',
        'batch_size': 4,
        'media_type': 'wav',
        'streaming_mode': 'false',
    }
    
    try:
          # Use aiohttp for asynchronous HTTP requests
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:

                # Check if the request was successful
                if response.status == 200:
                    audio_data = await response.read()
                    # Save the audio content to a file
                    with open('output/ttsoutput.wav', 'wb') as f:
                        f.write(audio_data)
                    print('Audio saved to output/ttsoutput.wav')
                else:
                    error_data = await response.json()
                    print(f'Error: {response.status}')
                    print(error_data)
                    return
    except aiohttp.ClientError as e:
        print(f'An error occurred during the HTTP request: {e}')
        return
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        return


    '''rvc = RVCInference(models_dir="./models", 
                    device="cuda:0",
                    f0method = "rmvpe",
                    f0up_key=0,
                    index_rate=0.5,
                    filter_radius=3,
                    resample_sr=0,
                    rms_mix_rate=1,
                    protect=0.33)
    print("List of models: ", rvc.list_models())

    rvc.load_model("baldi")
    rvc.infer_file("output/ttsoutput.wav", "output/rvcoutput.wav")'''
    
    # Wait a moment to ensure audio file is ready
    #await asyncio.sleep(1)

    cfg.voice_client.play(discord.FFmpegPCMAudio(executable="C:/ffmpeg/bin/ffmpeg.exe", source="output/ttsoutput.wav"))
    
    print("\n--- GPT-SoVITS/RTC Generated & Played Audio. ---\n")

async def gen_with_sovits_streaming(input_text, ctx):
    
    # API configuration
    host = '127.0.0.1'
    port = 9880
    url = f'http://{host}:{port}/tts'

    # Parameters for the request
    params = {
        'text': input_text,  
        'text_lang': 'en',
        'ref_audio_path': 'balditest.wav',
        'prompt_lang': 'en',
        'prompt_text': 'Oh, Hi. Welcome to my school house!',
        'text_split_method': 'cut0',
        'batch_size': 4,
        'media_type': 'wav',
        'streaming_mode': 'True',
        'cumulation_amount': 10,
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    buffer = b''  # Buffer to hold data until header is processed
                    header_size = 44  # Standard WAV header size
                    header_parsed = False
                    temp_file = "temp_audio.wav"

                    with open(temp_file, 'wb') as f:
                        async for chunk in response.content.iter_chunked(4096):
                            if chunk:
                                if not header_parsed:
                                    buffer += chunk
                                    if len(buffer) >= header_size:
                                        # Parse WAV header
                                        wav_header = buffer[:header_size]
                                        wav_file = wave.open(io.BytesIO(wav_header), 'rb')
                                        channels = wav_file.getnchannels()
                                        sample_rate = wav_file.getframerate()
                                        wav_file.close()

                                        # Write the header and remaining data to a temporary file
                                        f.write(buffer)
                                        header_parsed = True
                                        buffer = b''  # Clear buffer
                                else:
                                    # Write remaining data to the temporary file
                                    f.write(chunk)

                    # Play the audio in the Discord voice channel
                    audio_source = discord.FFmpegOpusAudio(executable="C:/ffmpeg/bin/ffmpeg.exe", source=temp_file)
                    ctx.voice_client.play(audio_source)
                else:
                    print(f'Error: {response.status}')
                    # Print the error message from the API
                    try:
                        error_message = await response.json()
                        print(error_message)
                    except ValueError:
                        error_message = await response.text()
                        print(error_message)
    except Exception as e:
        print(f'An error occurred: {e}')

    print("\n--- GPT-SoVITS/RTC Generated & Played Audio. ---\n")

# Text_to_audio_played function - This is used to generate a mp3 file from openai's reply and then play it
async def text_to_audio_played(input_text, ctx, voice="Bill"):

    if cfg.voice_client.is_playing(): return

    response_start_time = time.time()
    #await gen_with_elevenlabs(input_text, voice)
    #await gen_with_sovits(input_text, ctx)
    await gen_with_sovits_streaming(input_text, ctx)

    response_time = time.time() - response_start_time
    print(f"Response time: {int(response_time // 60):02d}:{int(response_time % 60):02d}.{int((response_time % 1) * 1000):03d}")

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
        cfg.voice_client.listen(voice_recv.extras.SpeechRecognitionSink(process_cb=cb, phrase_time_limit=5))
        await ctx.send(f"I am now listening!")
        print("The bot is listening to user")
    else:
        mentioned_user = ctx.message.mentions[0]
        cfg.listen_to_name = mentioned_user.name

        # Check if the mentioned user is in the same voice channel as the bot
        if not mentioned_user.voice or mentioned_user.voice.channel != cfg.voice_client.channel:
            await ctx.send(f"{mentioned_user.display_name} is not in the same voice channel as me!")
            return

        cfg.voice_client.listen(voice_recv.UserFilter(voice_recv.extras.SpeechRecognitionSink(process_cb=cb, phrase_time_limit=5), mentioned_user))
        await ctx.send(f"Now listening to {mentioned_user.display_name}!")
        print(f"The bot is listening to {mentioned_user.display_name}")

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
            print(f"Did not recognize {user_name if user else 'Unknown User'}'s audio")
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
        #asyncio.run(text_to_audio_played(openai_answer, vc=vc, voice=ELEVENLABS_VOICE))
        #return final_result
