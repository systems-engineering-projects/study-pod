"""simple validation of the response including:
The reply parses with json.loads and comes back as a list.
Every turn has exactly the keys speaker and text, and speaker is HOST_A or HOST_B.
No text is empty or only whitespace.
"""

def validate_notes(notes) -> list:
    errors = []

    if not isinstance(notes, list):
        errors.append(f"Expecting a list of notes bullets. Got {notes}")
        return errors   

    if not 3 <= len(notes) <= 6:
        errors.append(f"expected 3 to 6 notes, got {len(notes)}")

    for i, note in enumerate(notes):
        if not isinstance(note, str):
            errors.append(f"note {i} must be a string")
            continue
        if not note.strip():
            errors.append(f"note {i} text is empty or whitespace")

    return errors

def validate_script(turns, min_turns=6, max_turns=10) -> list:

    errors = []

    if not isinstance(turns, list):
        errors.append(f"Expecting a list of turns. Got {turns}")
        return errors

    if not min_turns <= len(turns) <= max_turns:
        errors.append(f"expected {min_turns} to {max_turns} turns, got {len(turns)}")
    prev = None
    seen = set()
    for i, turn in enumerate(turns):
        if not isinstance(turn, dict) or set(turn) != {"speaker", "text"}:
            errors.append(f"turn {i} must have exactly speaker and text")
            continue

        if not turn["speaker"]:
            errors.append(f"Expecting a speaker tag. Got {turn}")
        else:
            if turn["speaker"] not in ["HOST_A","HOST_B"]:
                errors.append(f"Expecting only host_a or Host_b speaker. Got {turn["speaker"]}")

        text = turn["text"]
        if not str(text).strip():
            errors.append(f"turn {i} text is empty or whitespace")

        else:
            if turn["text"] == "":
                errors.append(f"Expecting a text tag. Got {turn["text"]}")

        if turn["speaker"] == prev:
            errors.append(f"Speakers should take turns.  turn {i} repeats speaker {turn["speaker"]}")

        prev = turn["speaker"]

        seen.add(turn["speaker"])

    if seen != {"HOST_A", "HOST_B"}:
        errors.append(f"should include both speakers.  Only heard: {seen}")


    return errors




same_speaker = [
    {"speaker": "HOST_A", "text": "First."},
    {"speaker": "HOST_A", "text": "Second, same speaker."},
]

empty_text = [{"speaker": "HOST_A", "text": ""}]

good = [
    {"speaker": "HOST_A", "text": "Plants turn light into food."},
    {"speaker": "HOST_B", "text": "Where does the light go?"},
    {"speaker": "HOST_A", "text": "Chlorophyll in the leaves absorbs it."},
    {"speaker": "HOST_B", "text": "And then what happens to the water?"},
    {"speaker": "HOST_A", "text": "The energy splits water and helps build sugar."},
    {"speaker": "HOST_B", "text": "From carbon dioxide, right?"},
]

oops = "oops"

no_text_tag = [{"speaker": "HOST_A"}]

bonus = [{"oops": 1}, {"speaker": "HOST_A", "text": "hi"}]

def main():
    print("same speaker:", validate_script(same_speaker))
    print("empty text:", validate_script(empty_text))
    print("oops:", validate_script(oops))
    print("no_text_tag:", validate_script(no_text_tag))
    print("good:", validate_script(good))
    print("bonus:", validate_script(bonus))

if __name__ == "__main__":
    main()