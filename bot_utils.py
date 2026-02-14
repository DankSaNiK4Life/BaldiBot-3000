from config import Config as cfg
import base64
import requests
import random
import time
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
import uvicorn

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
    if os.path.exists("temp_audio.mp3"):
        return FileResponse("temp_audio.mp3", media_type="audio/mpeg")
    return {"error": "No audio file found"}

def start_http_server():
    uvicorn.run(app, host="0.0.0.0", port=10000, log_level="warning")

def set_source_visibility(ws, scene_name, source_name, source_visible=True):
        response = ws.call(requests.GetSceneItemId(sceneName=scene_name, sourceName=source_name))
        myItemID = response.datain['sceneItemId']
        ws.call(requests.SetSceneItemEnabled(sceneName=scene_name, sceneItemId=myItemID, sceneItemEnabled=source_visible))