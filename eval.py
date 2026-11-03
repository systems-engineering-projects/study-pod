"""asks Grok to judge five random turns and prints a score like 5/5 grounded"""

import random
from script import client, _strip_json_fence
import json

def check_grounding(turns, entries) -> None:
    """entries is the list of chunks that we are testing the turns against"""


    # flatten entries to a string
    seen = []
    for entry in entries:
        for note in entry["notes"]:
            if note not in seen:
                seen.append(note)
    notes_text = "\n".join(f"- {note}" for note in seen)


    picked = random.sample(list(enumerate(turns)), k=min(5, len(turns)))
    picked.sort()  # (index, turn) pairs, back in script order

    prompt = """Is this spoken line supported by the notes in notes.json?
    Return a response like: {"grounded": "yes", "claim": ""}"""

    yeses = 0

    for i, turn in picked:
        print(i, turn["speaker"], turn["text"])
        response = client.responses.create(
            model="grok-4.7",
            input=f"{prompt}\n\nStudy notes:\n{notes_text}\n\nSpoken line:\n{turn['text']}"        )

        raw = response.output_text

        try:
            verdict = json.loads(_strip_json_fence(raw))
            if verdict["grounded"] == "yes":
                yeses += 1
            else:
                print(verdict["claim"])
        except json.JSONDecodeError:
            # Keep the raw reply visible. A fenced or chatty answer is why this failed.
            print(raw)
            return None

    print(f"{yeses}/{len(picked)} grounded")


if __name__ == "__main__":
    with open("notes.json", encoding="utf-8") as f:
        entries = json.load(f)
    with open("script.json", encoding="utf-8") as f:
        turns = json.load(f)
    check_grounding(turns, entries)