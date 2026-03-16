import base64, requests, random, os, uvicorn, json
from config import Config as cfg
from obswebsocket import requests as obs_requests
from fastapi import FastAPI
from fastapi.responses import FileResponse
from personalities import Personalities as p

def encode_image_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode('utf-8')
    return None

# Get_real_name - This is used to get the real name from the Discord username
def get_real_name(user_name):
    return cfg.USERNAME_TO_REALNAME.get(user_name, user_name)  # Default to the original username if not found

# play random sounds at random intervals to make the bot more lively and engaging
def get_random_sound():
    sound_files = [f for f in os.listdir(cfg.SOUND_FOLDER) if f.endswith('.mp3')]

    if sound_files:
        sound_file = random.choice(sound_files)
        print(f"Random sound selected: {sound_file}") 
        sound_file_dir = os.path.join(cfg.SOUND_FOLDER, sound_file)
        return sound_file_dir

app = FastAPI()

@app.get("/audio.mp3")
async def get_audio():
    if os.path.exists("./sounds/temp_audio.mp3"):
        return FileResponse("./sounds/temp_audio.mp3", media_type="audio/mpeg")
    return {"error": "No audio file found"}

def start_http_server():
    uvicorn.run(app, host="0.0.0.0", port=10000, log_level="warning")

def set_source_visibility(ws, scene_name, source_name, source_visible=True):
        response = ws.call(obs_requests.GetSceneItemId(sceneName=scene_name, sourceName=source_name))
        myItemID = response.datain['sceneItemId']
        ws.call(obs_requests.SetSceneItemEnabled(sceneName=scene_name, sceneItemId=myItemID, sceneItemEnabled=source_visible))

def get_source_visibility(ws, scene_name, source_name):
    id_response = ws.call(obs_requests.GetSceneItemId(sceneName=scene_name, sourceName=source_name))
    item_id = id_response.datain['sceneItemId']
    status_response = ws.call(obs_requests.GetSceneItemEnabled(sceneName=scene_name, sceneItemId=item_id))

    return status_response.datain['sceneItemEnabled']

# This function is used to change the bot's personality (e.g. change the system message, change the avatar, change the ElevenLabs voice/model, etc.)
async def set_personality(personality_name, ctx, bot):
    # ------- Sane Baldi ------- #
    if personality_name.lower() == "sane baldi":
        with open("./images/pfps/RealisticBaldiAI.png", "rb") as image:
            new_avatar = image.read()
        await bot.user.edit(avatar=new_avatar)
        cfg.DEFAULT_SYSTEM_MESSAGE = p.SANE_BALDIS_FIRST_SYSTEM_MESSAGE
        cfg.BACKUP_JSON_FILE = "backups/SaneBaldiChatHistoryJsonBackup.json"
        cfg.elevenlabs_voice = "vrkuGKtvocSoZvsaAeUM"
        cfg.elevenlabs_model = "eleven_v3"
        cfg.ai_image_source = "RealisticBaldiAI"
        cfg.message_source = "RealisticAIBaldiMessage"
        cfg.join_vc_audio = "./sounds/RealisticBaldiAIVoiceTest.mp3"
        p.CURRENT_PERSONALITY = "sane baldi"
    
    # --------- Baldi --------- #
    elif personality_name.lower() == "baldi":
        with open("./images/pfps/BaldiAI.png", "rb") as image:
            new_avatar = image.read()
        await bot.user.edit(avatar=new_avatar)
        cfg.DEFAULT_SYSTEM_MESSAGE = p.BALDIS_FIRST_SYSTEM_MESSAGE
        cfg.BACKUP_JSON_FILE = "backups/BaldiHistoryJsonBackup.json"
        cfg.elevenlabs_voice = "CGOMbDUL52Yuc7oiDIm8"
        cfg.elevenlabs_model = "eleven_multilingual_v2"
        cfg.ai_image_source = "BaldiAI"
        cfg.message_source = "AIBaldiMessage"
        cfg.join_vc_audio = "./sounds/BaldiAIVoiceTest.mp3"
        p.CURRENT_PERSONALITY = "baldi"

    # --------- Sexy Baldi --------- #
    elif personality_name.lower() == "sexy baldi":
        with open("./images/pfps/SexyBaldiAI.png", "rb") as image:
            new_avatar = image.read()
        await bot.user.edit(avatar=new_avatar)
        cfg.DEFAULT_SYSTEM_MESSAGE = p.SEXY_BALDIS_FIRST_SYSTEM_MESSAGE
        cfg.BACKUP_JSON_FILE = "backups/SexyBaldiHistoryJsonBackup.json"
        cfg.elevenlabs_voice = "TC0Zp7WVFzhA8zpTlRqV"
        cfg.elevenlabs_model = "eleven_v3"
        cfg.ai_image_source = "SexyBaldiAI"
        cfg.message_source = "SexyBaldiMessage"
        cfg.join_vc_audio = "./sounds/SexyBaldiAIVoiceTest.mp3"
        p.CURRENT_PERSONALITY = "sexy baldi"

    # --------- Shadow Baldi --------- #
    elif personality_name.lower() == "shadow baldi":
        with open("./images/pfps/ShadowTheMelon.png", "rb") as image:
            new_avatar = image.read()
        await bot.user.edit(avatar=new_avatar)
        cfg.DEFAULT_SYSTEM_MESSAGE = p.SHADOW_BALDIS_FIRST_SYSTEM_MESSAGE
        cfg.BACKUP_JSON_FILE = "backups/ShadowBaldiHistoryJsonBackup.json"
        cfg.elevenlabs_voice = "7squ7rvxEIZ2rYy7KYPP"
        cfg.elevenlabs_model = "eleven_v3"
        cfg.ai_image_source = "ShadowTheMelon"
        cfg.message_source = "ShadowTheMelonMessage"
        cfg.join_vc_audio = "./sounds/ShadowTheMelonVoiceTest.mp3"
        p.CURRENT_PERSONALITY = "shadow baldi"

    # --------- Protectron --------- #
    elif personality_name.lower() == "protectron":
        with open("./images/pfps/Protectron.png", "rb") as image:
            new_avatar = image.read()
        await bot.user.edit(avatar=new_avatar)
        cfg.DEFAULT_SYSTEM_MESSAGE = p.PROTECTRON_FIRST_SYSTEM_MESSAGE
        cfg.BACKUP_JSON_FILE = "backups/ProtectronHistoryJsonBackup.json"
        cfg.elevenlabs_voice = "17emZEdpFxzVxRKIMpMN"
        cfg.elevenlabs_model = "eleven_multilingual_v2"
        cfg.ai_image_source = "Protectron"
        cfg.message_source = "ProtectronMessage"
        cfg.join_vc_audio = "./sounds/ProtectronVoiceTest.mp3"
        p.CURRENT_PERSONALITY = "protectron"

    # --------- Grandpa Melon --------- #
    elif personality_name.lower() == "grandpa":
        with open("./images/pfps/GrandpaMelon.png", "rb") as image:
            new_avatar = image.read()
        await bot.user.edit(avatar=new_avatar)
        cfg.DEFAULT_SYSTEM_MESSAGE = p.GRANDPA_FIRST_SYSTEM_MESSAGE
        cfg.BACKUP_JSON_FILE = "backups/GrandpaMelonHistoryJsonBackup.json"
        cfg.elevenlabs_voice = "MKlLqCItoCkvdhrxgtLv"
        cfg.elevenlabs_model = "eleven_multilingual_v2"
        cfg.ai_image_source = "GrandpaMelon"
        cfg.message_source = "GrandpaMelonMessage"
        cfg.join_vc_audio = "./sounds/GrandpaMelonVoiceTest.mp3"
        p.CURRENT_PERSONALITY = "grandpa"
    
    # If the personality name is not recognized, send an error message
    else:
        print(f"Unknown personality: {personality_name}")
        if ctx != None: await ctx.send("Unknown personality! use 'baldi commands' to see the list of available personalities.")
        return
    
    # Load chat history from file if it exists
    if os.path.exists(cfg.BACKUP_JSON_FILE):
        with open(cfg.BACKUP_JSON_FILE, "r") as file:
            try:
                cfg.chat_history = json.load(file)  # Load JSON data into cfg.chat_history list
                print("--- Personality Chat history was loaded. ---")
            except json.JSONDecodeError:
                print("--- Personality Chat history file is empty or corrupted. Starting fresh. ---")
    else:
        print("--- JSON file does not exist. Will create a new one on the first message ---")

    # After changing the personality, we need to update the system message in the chat history so the AI can use the new personality immediately
    cfg.chat_history.remove(cfg.chat_history[0])
    cfg.chat_history.insert(0, cfg.DEFAULT_SYSTEM_MESSAGE)

    print("--- Personality has been set ---")