from config import Config as cfg
import base64
import pyscreenshot as ImageGrab

# Take_screenshot function - This is called when the user says a trigger phrase (E.g. "do you see this?") and saves a image of their screen
def take_screenshot():
    print("Taking screenshot...")

    image_name = "screenshot_message.jpg"
    screenshot = ImageGrab.grab()

    filepath = f"images/{image_name}"

    screenshot.save(filepath)

    print("Screenshot taken!")

    return filepath

# Encode_images function - This is used to correctly encode the screenshot before it is sent to openai
def encode_image(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Get_real_name - This is used to get the real name from the Discord username
def get_real_name(user_name):
    return cfg.USERNAME_TO_REALNAME.get(user_name, user_name)  # Default to the original username if not found
