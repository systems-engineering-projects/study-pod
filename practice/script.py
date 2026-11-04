import os
from dotenv import load_dotenv
from openai import OpenAI   #this is a python library not the brand openai
#The library is a client that knows how to send a Responses API call and read the reply. xAI’s HTTP API uses that same shape, so their quickstart installs that library and points it at xAI.


import json
from validate import validate_script
import requests
from audio import audio

load_dotenv()

paragraph = """
Photosynthesis is how plants turn light into food. Chlorophyll in the leaves
absorbs light. That energy splits water and helps build sugar from carbon dioxide.
"""

prompt = """You are going to present a pretend podcast with two roles HOST_A and HOST_B. 
    HOST_A explains, and HOST_B is curious and asks the questions a learner would ask.
    Use only the source paragraph, with no outside facts.
    Limit is 6 to 10 turns, alternating, with each turn spoken aloud in one to three sentences.
    Return only a JSON list structured like this [
  {"speaker": "HOST_A", "text": "..."},
  {"speaker": "HOST_B", "text": "..."}
], with no prose or code fences around it."""

client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
)

response = client.responses.create(
    model="grok-4.7",
    input=f"{prompt}\n\nSource paragraph:\n{paragraph}",
)

def speak(text, voice_id, path):
    """Different call to a different api (voice) than the model that formed the text answer"""

    response = requests.post(
        "https://api.x.ai/v1/tts",
        headers={
            "Authorization": f"Bearer {os.environ['XAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={"text": text, "voice_id": voice_id, "language": "en"},
    )
    response.raise_for_status()
    with open(path, "wb") as f:
        f.write(response.content)

raw = response.output_text
try:
    turns = json.loads(raw)

except json.JSONDecodeError:
    print(raw)
    
else:
    # print(validate_script(turns))
    errors = validate_script(turns)
    # print(turns)
    audio_files = []
    if not errors:
        for i, turn in enumerate(turns):
            text = turn["text"]
            if turn["speaker"] == "HOST_A":
                voice_id = "eve"
            else:
                voice_id = "ara"
            path = f"turn_{i:02d}.mp3"
            audio_files.append(path)
            speak(text, voice_id, path)

    #audio was generated, let's put them into one file w pauses
    audio(audio_files)



