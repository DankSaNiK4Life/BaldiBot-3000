from config import Config as cfg
import base64
import requests

def encode_image_from_url(url):
    response = requests.get(url)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode('utf-8')
    return None

# Get_real_name - This is used to get the real name from the Discord username
def get_real_name(user_name):
    return cfg.USERNAME_TO_REALNAME.get(user_name, user_name)  # Default to the original username if not found
