import base64, requests, random, os, uvicorn
from config import Config as cfg
from obswebsocket import obsws, requests as obs_requests
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
    
    # If the personality name is not recognized, send an error message
    else:
        print(f"Unknown personality: {personality_name}")
        await ctx.send("Unknown personality! use 'baldi commands' to see the list of available personalities.")
        return
    
    # After changing the personality, we need to update the system message in the chat history so the AI can use the new personality immediately
    cfg.chat_history.remove(cfg.chat_history[0])
    cfg.chat_history.insert(0, cfg.DEFAULT_SYSTEM_MESSAGE)

    print("--- Personality has been set ---")

def check_obs_connection():
    ws = obsws(cfg.WEBSOCKET_HOST, cfg.WEBSOCKET_PORT, cfg.WEBSOCKET_PASSWORD, timeout=3)
    try:
        ws.connect()
        print("Successfully connected to OBS WebSocket.")
        ws.disconnect()
        return True
    except ConnectionRefusedError:
        print("OBS is not running or WebSocket is disabled.")
    except Exception as e:
        print(f"Connection failed: {e}")
    return False