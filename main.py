"""One command from a source to a playable episode.

The long work lives in script.py: loading, chunking, summarizing each
chunk, and writing the two-host script. This file only chooses the
arguments and runs those steps in order. Map-reduce is the reason for
the order. A long source cannot fit in one prompt, so each chunk becomes
short notes first, and one later call writes the conversation from all
of the notes together.
"""

import argparse
import json
import sys

from audio import audio
from script import (
    chunk_text,
    load_source,
    make_notes,
    speak,
    turn_range,
    turns_for_minutes,
    write_script,
)
from validate import validate_script
from eval import check_grounding


def build_parser() -> argparse.ArgumentParser:
    # --source is required because there is no default document.
    # --out defaults so a plain run still leaves episode.mp3 in this folder.
    # --minutes is optional. Without it, the notes themselves pick the length.
    parser = argparse.ArgumentParser(
        description="Turn a PDF, notes file, or web page into a two-host study episode.",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="A .pdf, .txt, or .md path, or an http(s) URL",
    )
    parser.add_argument(
        "--out",
        default="episode.mp3",
        help="Where to write the finished episode (default: episode.mp3)",
    )
    parser.add_argument(
        "--minutes",
        type=float,
        default=None,
        help="Optional target length in minutes",
    )
    return parser


def choose_turn_window(entries, minutes) -> tuple[int, int]:
    """Pick how many turns to ask for, and say which numbers decided it.

    turn_range counts distinct notes, so a short source stays a short
    episode. --minutes is a listener request. Capping it by the note
    range keeps the script from inventing facts just to fill time.
    """
    note_low, note_high = turn_range(entries)
    if minutes is None:
        print(f"Notes support {note_low} to {note_high} turns")
        return note_low, note_high

    asked_low, asked_high = turns_for_minutes(minutes)
    min_turns = min(asked_low, note_high)
    max_turns = min(asked_high, note_high)
    # The floor stays 6, and the low end cannot sit above the high end
    # after the notes cap both sides.
    min_turns = max(6, min(min_turns, max_turns))
    print(
        f"Notes support {note_low} to {note_high} turns; "
        f"--minutes asked for {asked_low} to {asked_high}; "
        f"using {min_turns} to {max_turns}"
    )
    return min_turns, max_turns


def main() -> None:
    args = build_parser().parse_args()
    if args.minutes is not None and args.minutes <= 0:
        print("--minutes must be greater than 0")
        sys.exit(1)

    # Loaders raise ValueError for a scanned PDF, an empty file, or a
    # type this app does not read. Print that and stop before any API call.
    try:
        source_text = load_source(args.source)
    except ValueError as err:
        print(err)
        sys.exit(1)
    print(f"Loaded {len(source_text)} characters from {args.source}")

    # Chunks share a little text so a sentence on a boundary is whole in
    # one of them. An empty source becomes no chunks, and there is nothing
    # left to summarize.
    chunks = chunk_text(source_text)
    if not chunks:
        print("No text to summarize.")
        sys.exit(1)

    entries = []
    for i, chunk in enumerate(chunks):
        # Printed before the call so a slow chunk still shows which one it is.
        print(f"Chunk {i + 1}/{len(chunks)} summarized")
        notes = make_notes(chunk)
        if notes is None:
            print(f"Chunk {i + 1}/{len(chunks)} skipped")
            continue
        entries.append({"chunk": i, "notes": notes})

    # notes.json is the inspectable map output. The reduce reads `entries`
    # in memory; the file is so a run can be checked without another call.
    with open("notes.json", "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(entries)} chunks to notes.json")

    if not entries:
        print("No notes were produced, so there is nothing to turn into a script.")
        sys.exit(1)

    min_turns, max_turns = choose_turn_window(entries, args.minutes)
    print(f"Writing a script of {min_turns} to {max_turns} turns")
    turns = write_script(entries, min_turns, max_turns)
    if turns is None:
        print("The script reply was not JSON.")
        sys.exit(1)

    # Validation is free and certain. TTS is not, so a bad script stops here.
    errors = validate_script(turns, min_turns, max_turns)
    if errors:
        print("Script failed validation:")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)
    print(f"Script passed validation ({len(turns)} turns)")

    # dump turns the same way you dump entries so we can grab it for eval
    with open("script.json", "w", encoding="utf-8") as f:
        json.dump(turns, f, indent=2, ensure_ascii=False)

    # Zero-padded names sort in spoken order when the stitcher sorts paths.
    # eve and ara are the two built-in voices, one per host.
    audio_files = []
    for i, turn in enumerate(turns):
        print(f"Turn {i + 1}/{len(turns)} voiced")
        voice_id = "eve" if turn["speaker"] == "HOST_A" else "ara"
        path = f"turn_{i:02d}.mp3"
        speak(turn["text"], voice_id, path)
        audio_files.append(path)

    # Short silences between clips are added inside audio().
    audio(audio_files, args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

    with open("notes.json", encoding="utf-8") as f:
        entries = json.load(f)
    with open("script.json", encoding="utf-8") as f:
        turns = json.load(f)
    check_grounding(turns, entries)