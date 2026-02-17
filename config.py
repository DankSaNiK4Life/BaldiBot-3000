import os, requests
from elevenlabs.client import ElevenLabs
from personalities import Personalities as p

class Config:
    
    # ------------- API KEYS (CONSTANTS) ------------- #

    AZURE_TTS_KEY = os.getenv("AZURE_TTS_KEY")
    AZURE_TTS_REGION = os.getenv("AZURE_TTS_REGION")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
    STREAMERBOT_WEBHOOK_URL = os.getenv("STREAMERBOT_WEBHOOK_URL")
    WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST")
    WEBSOCKET_PORT = os.getenv("WEBSOCKET_PORT")
    WEBSOCKET_PASSWORD = os.getenv("WEBSOCKET_PASSWORD")
    SFTP_HOST = os.getenv("SFTP_HOST")
    SFTP_PORT = os.getenv("SFTP_PORT")
    SFTP_USERNAME = os.getenv("SFTP_USERNAME")
    SFTP_PASSWORD = os.getenv("SFTP_PASSWORD")

    # ------------------- CONSTANTS ------------------- #

    MAX_DURATION = 30                                           # This is how long the user can speak for before the speech is sent
    SILENCE_TIMEOUT = 4                                         # This is how long the user needs to be silent for to be able to send their speech
    BACKUP_JSON_FILE = "backups/BaldiHistoryJsonBackup.json"    # Use JSON for structured data
    MAX_TOKENS = 6000                                           # Set a reasonable limit to avoid excessive costs (4000 tokens is about 3000 word)
    OWNER_ID = 205472888755716107                               # This is who the owner of the bot is (AKA Baldi The Melon Head)
    DEFAULT_SYSTEM_MESSAGE = p.BALDIS_FIRST_SYSTEM_MESSAGE      # This is the default system message (personality) that the bot will use on start
    SOUND_FOLDER = "./sounds/random sounds"                     # This is the folder where the sound files are stored
    RANDOM_SOUND_INTERVAL = (1200, 3600)                        # This is the interval (in seconds) at which random sounds will be played (Every 20 mins to 1 hour)
    LOG_CHANNEL_ID = 1471673659998343333                        # This is the channel ID of the channel where the bot will send logs (e.g. errors, when it starts listening, etc)


    # This is what shows when "baldi show commands" is used
    COMMANDS_LIST = f'''**Available commands for BaldiBot 3000: **
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
    `baldi die - turns off the bot
    baldi set obs - Turns On/Off OBS websockets`'''

    # This is a list of user IDs that the bot will trust to use important commands
    TRUSTED_USER_IDS = [                                        
        OWNER_ID, 
        257961792867663875, # Ishaq
        247009258099441664, # Shaun
        314124876745277440, # Ewan
        195309114967064587, # Fil
        872867731580530718, # Taylor
        838854430111301652, # Bailey
    ] 

    USERNAME_TO_REALNAME = {
    "baldithemelonhead": "Reece",
    "solidsnook_": "Ishaq",
    "marz_anteater": "Shaun",
    "cryptogenic7": "Ewan",
    "crocodilian_01": "Josh",
    "chdthunderc0ck": "Taylor",
    "melonssecretary": "Bailey",
    "kancelaria": "Fil",
    "ultra8486": "Shohrukhi",
    "etanyello": "Ethan",
    "kushki": "Kushki"
    }

    # -------------------- GLOBAL -------------------- #

    cb_ctx = None                                   # This is a global variable used in the cb function
    voice_client = None                             # This acts as a global voice client so I dont have to use it as a parameter for like every functions lol
    start_time = 0                                  # This is used later to check when the bot first started listening
    last_speech_time = 0                            # This is used later to check the last time the user spoke
    chat_history = []                               # This is used to store all previous chat messages so the AI can rememeber them
    all_results = []                                # This stores every thing the user has said during the listening phase
    last_user_message = " "                         # This is used for the "last" command to show the last message sent by the user
    last_bot_message = " "                          # This is used for the "last" command to show the last message sent by the bot
    listen_to_name = None                           # This is used to store the name of the user the bot is listening to
    random_sounds_enabled = True                    # This is used to enable or disable the random sounds feature
    elevenlabs_voice = "CGOMbDUL52Yuc7oiDIm8"       # Replace this with the name of whatever voice you have created on Elevenlabs (Baldi The Melon Head V2 - vrkuGKtvocSoZvsaAeUM, Baldi The Melon Head - CGOMbDUL52Yuc7oiDIm8)
    elevenlabs_model = "eleven_multilingual_v2"     # This is the ElevenLabs model we will be using for TTS
    ai_image_source = "BaldiAI"                     # This is the name of the image source in OBS that will show the AI's image (if using OBS for audio playback)
    message_source = "AIBaldiMessage"               # This is the name of the text source in OBS that will show the user's message (if using OBS for audio playback)
    join_vc_audio = "./sounds/BaldiAIVoiceTest.mp3" # This plays test audio when bot joins a vc to stop the sound cutting off at the start of first vc messages
    obs_enabled = False                             # This controls if the bot should use obs websockets or not

    eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) # This assigns the ElevenLabs client

    is_waiting_for_silence = False  # This is used to call the waiting_for_silence function in the cb function
    is_listen_to_all = False        # This is used to determine if the bot should listen to everyone or just someone specific

    # MIGHT NEED TO MOVE THIS TO A SEPERATE FILE LATER
    # Uses Streamer.bots Webhook feature to send messages to Twitch (E.g. ChatGPT responses)
    def send_to_twitch(reply_text):
        if not Config.STREAMERBOT_WEBHOOK_URL:
            print("Streamer.bot webhook URL is not set. Cannot send message to Twitch.")
            return

        payload = {
            "gpt_response": reply_text
        }

        try:
            response = requests.post(Config.STREAMERBOT_WEBHOOK_URL, json=payload)
            if response.status_code == 200 or response.status_code == 201:
                print("Message sent to Twitch successfully.")
            else:
                print(f"Failed to send message to Twitch. Status code: {response.status_code}")
        except Exception as e:
            print(f"An error occurred while sending message to Twitch: {e}")