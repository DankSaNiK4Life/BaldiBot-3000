from config import Config as cfg
from bot_utils import take_screenshot, encode_image
from openai import OpenAI
import tiktoken
import asyncio
import json
import openai

openai.api_key = cfg.OPENAI_API_KEY # This assigns the OpenAI API key
client = OpenAI() # This assigns the OpenAI client

# Num_tokens_from_messages function - This is used to determine the amount of tokens the chat history has in total
def num_tokens_from_messages(messages, model="gpt-4o"):
    try:
      encoding = tiktoken.encoding_for_model(model)
      num_tokens = 0
      for message in messages:
          num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
          for key, value in message.items():
              num_tokens += len(encoding.encode(value))
              if key == "name":  # if there's a name, the role is omitted
                  num_tokens += -1  # role is always required and always 1 token
      num_tokens += 2  # every reply is primed with <im_start>assistant
      return num_tokens
    except Exception:
        raise NotImplementedError(f"num_tokens_from_messages() is not presently implemented for model {model}.")

# Chat_with_gpt function - This is the logic required to actually speak to openai and be able to gain a response (Uses num_tokens_from_messages)
async def chat_with_gpt(prompt, user_name):
    if not prompt:
        print("Didn't Recieve input!")
        return
    
    # Save the last message sent by the user (for the last command)
    cfg.last_user_message = prompt

    # Add our prompt into the chat history
    cfg.chat_history.append({"role": "user", "content": prompt, "name": user_name})
    print(f"Added messgage to history! New total token length is: {num_tokens_from_messages(cfg.chat_history)}")

    # Ensure we don't exceed the token limit
    while num_tokens_from_messages(cfg.chat_history) > cfg.MAX_TOKENS:
        cfg.chat_history.pop(1)  # We skip the 1st message since it's the system message
        print(f"Popped a message! New token length is: {num_tokens_from_messages(cfg.chat_history)}")

    if cfg.is_image_message:
        print("Showing ChatGPT a image...")
        base64_image = encode_image(take_screenshot())

        # Wait a second or 2 for the screenshot to be taken
        await asyncio.sleep(2)

        image_message = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=image_message,
            max_tokens=300,
        )

        # adds image to chat history
        #cfg.chat_history.append(image_message)

        cfg.is_image_message = False
    else:
        print("Asking ChatGPT a question...")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=cfg.chat_history,
            max_tokens=300,
        )

    # Add this answer to our chat history
    cfg.chat_history.append({"role": response.choices[0].message.role, "content": response.choices[0].message.content})

    # Save updated chat history to file
    with open(cfg.BACKUP_JSON_FILE, "w") as file:
        json.dump(cfg.chat_history, file, indent=4)  # Save as readable JSON

    # Save the last message sent by the bot (for the last command)
    cfg.last_bot_message = response.choices[0].message.content.strip()
    
    # Process the answer
    return response.choices[0].message.content.strip()
