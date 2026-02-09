from config import Config as cfg
from bot_utils import get_real_name
from elevenlabs import save
from discord.ext import voice_recv
from openai_chat import chat_with_gpt
import time
import asyncio
import discord
import speech_recognition as sr
import aiohttp
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])
import wave
import io
import assemblyai as aai
import tempfile

# Dummy sink that discards audio data (here for now until I figure out a way to clear audio data properly lol)
class DummySink(voice_recv.AudioSink):
    def write(self, user, data):
        pass  # Discard the audio data
    
    def cleanup(self):
        pass  # No cleanup needed for this dummy sink

    def wants_opus(self):
        return False  # Indicate that this sink does not want Opus-encoded audio
    
def on_turn(transcript):
    if transcript.text:
        print(f"Transcript: {transcript.text}")

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
from config import Config as cfg
from bot_utils import get_real_name
from elevenlabs import save
from discord.ext import voice_recv
from openai_chat import chat_with_gpt
import time
import asyncio
import discord
import speech_recognition as sr
import aiohttp
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])
import wave
import io
import assemblyai as aai
from assemblyai.streaming.v3 import (
    StreamingClient, 
    StreamingClientOptions, 
    StreamingParameters,
    StreamingEvents,
    TurnEvent,
    BeginEvent,
    StreamingError
)

# Dummy sink that discards audio data (here for now until I figure out a way to clear audio data properly lol)
class DummySink(voice_recv.AudioSink):
    def write(self, user, data):
        pass  # Discard the audio data
    
    def cleanup(self):
        pass  # No cleanup needed for this dummy sink

    def wants_opus(self):
        return False  # Indicate that this sink does not want Opus-encoded audio
    
def on_turn(transcript):
    if transcript.text:
        print(f"Transcript: {transcript.text}")

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

        cfg.voice_client.listen(voice_recv.UserFilter(voice_recv.extras.SpeechRecognitionSink(process_cb=cb, phrase_time_limit=5), mentioned_user))
        await ctx.send(f"Now listening to {mentioned_user.display_name}!")
        print(f"The bot is listening to {mentioned_user.display_name}")

# Cb function - This is a callback function that vc.listen() uses to actually recognize and listen to the user (This calls wait_for_silence)
def cb(user: discord.Member, audio: sr.AudioData, third=None):
    user_name = user.display_name if isinstance(user, discord.Member) else "Unknown User"
    
    try:
        # Save audio to a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            audio_data = audio.get_wav_data()
            temp_file.write(audio_data)
            temp_file_path = temp_file.name
        
        # Upload the audio file to AssemblyAI
        async def transcribe_audio():
            url = 'https://api.assemblyai.com/v2/upload'
            headers = {'authorization': cfg.ASSEMBLYAI_API_KEY}

            # Upload the audio file to AssemblyAI
            async with aiohttp.ClientSession() as session:
                with open(temp_file_path, 'rb') as f:
                    file = f.read()
                    async with session.post(url, headers=headers, data=file) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            audio_url = data['upload_url']
                            print(f"Uploaded to AssemblyAI: {audio_url}")
                        else:
                            print("Error uploading audio to AssemblyAI.")
                            return

            # Request transcription
            transcribe_url = 'https://api.assemblyai.com/v2/transcript'
            json_data = {'audio_url': audio_url}
            async with aiohttp.ClientSession() as session:
                async with session.post(transcribe_url, headers=headers, json=json_data) as response:
                    if response.status == 200:
                        transcript_data = await response.json()
                        transcript_id = transcript_data['id']
                        print(f"Transcript request sent. ID: {transcript_id}")
                        # Check the transcript status
                        await check_transcription_status(transcript_id)
                    else:
                        print(f"Error sending transcription request: {response.status}")
                        return

        # Define a function to check transcription status
        async def check_transcription_status(transcript_id):
            status_url = f'https://api.assemblyai.com/v2/transcript/{transcript_id}'
            headers = {'authorization': cfg.ASSEMBLYAI_API_KEY}
            async with aiohttp.ClientSession() as session:
                while True:
                    async with session.get(status_url, headers=headers) as resp:
                        if resp.status == 200:
                            status_data = await resp.json()
                            if status_data['status'] == 'completed':
                                transcript_text = status_data['text']
                                print(f"Recognized text from {user_name}: {transcript_text}")
                                if transcript_text:  # If a transcript is available
                                    cfg.all_results.append(transcript_text)
                                    cfg.last_speech_time = time.time()  # Reset silence timer
                                break
                            elif status_data['status'] == 'failed':
                                print(f"Transcription failed: {status_data}")
                                break
                        await asyncio.sleep(1)  # Wait a bit before checking the status again

        # Run the transcription process
        asyncio.run(transcribe_audio())

    except Exception as e:
        print(f"An error occurred during the speech recognition process: {e}")

