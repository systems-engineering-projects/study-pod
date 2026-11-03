import os
from dotenv import load_dotenv
from openai import OpenAI   #this is a python library not the brand openai
#The library is a client that knows how to send a Responses API call and read the reply. xAI’s HTTP API uses that same shape, so their quickstart installs that library and points it at xAI.


import json
from validate import validate_notes, validate_script
import requests
import trafilatura
from audio import audio
from pypdf import PdfReader


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

def load_pdf(path) -> str:
    """Return all text from a PDF; raise ValueError if it's nearly empty."""
    # path = "sources/weathermaps.pdf"
    reader = PdfReader(path)

    pdf_string = ""

    for page in reader.pages:
        pdf_string += page.extract_text() or ""
        pdf_string += "\n\n"

    if len(pdf_string.strip()) <= 50:
        raise ValueError("no extractable text; this PDF may be a poor scan.") 

    return pdf_string


def load_url(url: str) -> str:
    """Download a page and return its main article text, without menus or ads."""
    # requests downloads the raw HTML. timeout stops a hung site from waiting forever.
    # A named User-Agent keeps some sites from rejecting the default "python-requests" label.
    response = requests.get(
        url,
        timeout=30,
        headers={"User-Agent": "study-pod/0.1 (personal study podcast)"},
    )
    # 404s and other HTTP errors become exceptions instead of empty HTML.
    response.raise_for_status()
    # trafilatura drops nav, footers, and scripts and keeps the readable body.
    text = trafilatura.extract(response.text)
    if not text or len(text.strip()) <= 50:
        raise ValueError(f"Could not extract main text from {url}")
    return text


def load_text(path: str) -> str:
    """Return the full contents of a .txt or .md notes file."""
    with open(path, encoding="utf-8") as file:
        text = file.read()
    if not text.strip():
        raise ValueError(f"{path} is empty.")
    return text


def load_source(source: str) -> str:
    """Pick a loader from the source string: URL, .pdf, .txt, or .md."""
    lowered = source.lower()
    # Check the URL first. A link like https://example.com/notes.pdf is still a web page,
    # so it must not fall through to the local PDF reader.
    if lowered.startswith("http://") or lowered.startswith("https://"):
        return load_url(source)
    if lowered.endswith(".pdf"):
        return load_pdf(source)
    if lowered.endswith(".txt") or lowered.endswith(".md"):
        return load_text(source)
    raise ValueError(
        "I can read a web URL, or a file ending in .pdf, .txt, or .md. "
        f"{source!r} is not one of those."
    )

def chunk_text(text, size=3000, overlap=300) -> list[str]:
    """Split text into pieces of at most `size` characters.

    A long source cannot go to the model in one prompt, so map-reduce
    summarizes one piece at a time. Neighbors share `overlap` characters
    so an idea that sits on the boundary is still whole in one of them.

    The hard cut is `start + size`. snap_split moves that cut backward to
    a paragraph break or sentence end so a piece does not stop mid-word.
    """
    # Tests: empty in, empty out. No blank chunk for the model to summarize.
    if not text:
        return []
    # Shorter than one window: return the original unchanged. Do not strip,
    # or this chunk would no longer equal the source text.
    if len(text) <= size:
        return [text]
    # The next start is `cut - overlap`. Overlap has to be smaller than size
    # or that start would never move forward and the loop would not end.
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be >= 0 and smaller than size")

    chunks = []
    start = 0
    while start < len(text):
        # Never plan a cut past the end of the text.
        proposed_end = min(start + size, len(text))
        # Last piece is already under `size`. Snapping it would drop the ending.
        if proposed_end == len(text):
            chunks.append(text[start:])
            break
        cut = snap_split(text, start, proposed_end, overlap)
        chunks.append(text[start:cut])
        # Step back by `overlap` so this piece's ending is the next piece's
        # opening. Dropping those shared characters and joining the rest
        # rebuilds the original text, which is how the overlap test works.
        start = cut - overlap
    return chunks


def snap_split(text, start, proposed_end, overlap) -> int:
    """Return a cut index in (start, ideal_end].

    The plain slice would end at ideal_end even in the middle of a word.
    Search backward for a cleaner boundary, and never past ideal_end,
    so the chunk stays at most `size` characters.
    """
    # The next chunk starts at `cut - overlap`. A cut at or before
    # `start + overlap` would leave that start in the same place or behind,
    # and the loop in chunk_text would not advance.
    left = start + overlap
    window = text[left:proposed_end]
    cuts = []
    # rfind walks from the right, so the index it returns is the boundary
    # nearest ideal_end. -1 means that marker is not in the window.
    paragraph = window.rfind("\n\n")
    if paragraph != -1:
        # +2 keeps both newlines in this chunk. The next chunk repeats
        # the overlap, then continues after the blank line.
        cuts.append(left + paragraph + 2)
    sentence = max(window.rfind(mark) for mark in ".!?")
    if sentence != -1:
        # +1 keeps the . ! or ? on this chunk instead of starting the next one.
        cuts.append(left + sentence + 1)
    if cuts:
        # A later index is closer to the hard cut. Prefer that one so we
        # do not shorten the chunk more than the nearest break requires.
        # A paragraph break after a period wins, because it sits further right.
        return max(cuts)
    # No paragraph or sentence in range. A space still ends on a word.
    space = window.rfind(" ")
    if space != -1:
        return left + space + 1
    # One long token with no break. Cut at the hard limit so the character
    # budget still holds; this is the only case that can split mid-word.
    return proposed_end


# One USD is 10^10 ticks. xAI documents this on
# https://docs.x.ai/developers/cost-tracking. The ticks are the billed
# amount for that call, after cache discounts, so this is a unit conversion
# and not a price looked up from a model card.
USD_TICKS = 10_000_000_000


def log_usage(response, label: str) -> None:
    """Print the token counts and billed cost for one Grok call.

    print(response.usage) was run once on a live reply so these names are
    the ones xAI actually sends. An episode is several map calls plus one
    script call, and each line is that call's share, so the lines add up
    to the episode. context_details is left off: it repeated the same
    token counts under another name.
    """
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    # check_make_notes replaces the client with a MagicMock. That mock
    # answers any attribute, so a missing usage object is not `None`.
    # Real counts are ints. Anything else is the test double, and we skip it.
    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)
    if not all(isinstance(n, int) for n in (input_tokens, output_tokens, total_tokens)):
        return

    details_in = getattr(usage, "input_tokens_details", None)
    details_out = getattr(usage, "output_tokens_details", None)
    cached_tokens = getattr(details_in, "cached_tokens", None)
    reasoning_tokens = getattr(details_out, "reasoning_tokens", None)
    # cost_in_usd_ticks is not on the OpenAI SDK's typed usage model.
    # xAI still sends it, and the SDK keeps it as an extra field.
    cost_in_usd_ticks = getattr(usage, "cost_in_usd_ticks", None)

    parts = [
        f"input_tokens={input_tokens}",
        f"output_tokens={output_tokens}",
        f"total_tokens={total_tokens}",
    ]
    if isinstance(cached_tokens, int):
        parts.append(f"cached_tokens={cached_tokens}")
    if isinstance(reasoning_tokens, int):
        parts.append(f"reasoning_tokens={reasoning_tokens}")
    if isinstance(cost_in_usd_ticks, int):
        parts.append(f"cost_in_usd_ticks={cost_in_usd_ticks}")
        parts.append(f"cost_usd={cost_in_usd_ticks / USD_TICKS:.6f}")
    print(f"{label} usage: " + " ".join(parts))


def make_notes(chunk) -> list[str]:

    prompt = """Please turn this source data into 3 to 6 short bullet notes, 
    using only facts stated in the source data.  
    Return only a JSON list structured like this ["...","..."], 
    with no prose or code fences around it. """
    # The map runs once per chunk and only pulls out facts already in the
    # source, so it does not need the model that writes the conversation.
    # grok-4.3 is the same Responses API at about half the text price
    # ($1.25 / $2.50 per million input / output tokens, versus $2.00 / $6.00
    # for grok-4.7). write_script stays on grok-4.7.
    response = client.responses.create(
        model="grok-4.3",
        input=f"{prompt}\n\nSource data:\n{chunk}",
        )
    # Map step. One line per chunk, so a long source shows where the cost went.
    log_usage(response, "Chunk notes")

    raw = response.output_text
    # notes = []
    # errors = []
    try:
        notes = json.loads(raw)
        # errors = validate_notes(notes)
        # return notes or errors
    except json.JSONDecodeError:
        print(raw)
        return None
    # else:
    #     return notes
    errors = validate_notes(notes)
    if errors:
        print(errors)
        return None
    return notes


def turn_range(entries) -> tuple[int, int]:
    """How many script turns these notes can support.

    Each distinct bullet is one fact worth saying. Explanations plus
    questions come to about 1.5 turns per bullet. The same pair is what
    the script prompt should request and what validate_script should accept.
    """
    seen = []
    for entry in entries:
        for note in entry["notes"]:
            if note not in seen:
                seen.append(note)
    # Floor of 6 keeps a short source a real conversation.
    # Ceiling of 24 keeps one script prompt from covering a whole book.
    target = max(6, round(len(seen) * 1.5))
    target = min(target, 24)
    slack = target // 4
    low = max(6, target - slack)
    high = min(24, target + slack)
    return low, high


def turns_for_minutes(minutes: float) -> tuple[int, int]:
    """Turn the optional --minutes flag into a script length.

    A turn is one to three spoken sentences, about 15 seconds, so four
    turns fill about a minute. The 6–24 clamp is the same one turn_range
    uses: under 6 is not a conversation, and over 24 is too much for one
    script prompt.
    """
    target = round(minutes * 4)
    target = max(6, min(24, target))
    slack = target // 4
    low = max(6, target - slack)
    high = min(24, target + slack)
    return low, high


def _strip_json_fence(raw: str) -> str:
    """Return the reply with a markdown code fence removed, if it has one.

    The prompt asks for a bare JSON list. The model still sometimes wraps
    that list in ```json ... ```, and json.loads rejects the fence.
    """
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    # The first line is ``` or ```json. Drop it, and drop a closing fence.
    lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def write_script(entries, min_turns, max_turns) -> list | None:
    """Reduce the mapped notes into one two-host script.

    make_notes summarized one chunk at a time. This call sees those facts
    together so the episode covers the whole source instead of one piece.
    Overlap repeats a boundary fact in two chunks, so repeated notes are
    dropped here the same way turn_range drops them when it counts.
    """
    seen = []
    for entry in entries:
        for note in entry["notes"]:
            if note not in seen:
                seen.append(note)
    notes_text = "\n".join(f"- {note}" for note in seen)

    # Same host rules as the milestone 1 prompt. The turn count comes from
    # the caller so a longer source, or --minutes, can ask for more than 6–10.
    prompt = f"""You are going to present a pretend podcast with two roles HOST_A and HOST_B.
    HOST_A explains, and HOST_B is curious and asks the questions a learner would ask.
    Use only the study notes below, with no outside facts.
    Write {min_turns} to {max_turns} turns, alternating, with each turn spoken aloud in one to three sentences.
    Return only a JSON list structured like this [
  {{"speaker": "HOST_A", "text": "..."}},
  {{"speaker": "HOST_B", "text": "..."}}
], with no prose or code fences around it."""

    # One call writes the whole episode. That is the conversation, so it
    # stays on grok-4.7. The per-chunk notes above already use grok-4.3.
    response = client.responses.create(
        model="grok-4.7",
        input=f"{prompt}\n\nStudy notes:\n{notes_text}",
    )
    # Reduce step. One call writes the script from every chunk's notes.
    log_usage(response, "Script")

    raw = response.output_text
    try:
        turns = json.loads(_strip_json_fence(raw))
    except json.JSONDecodeError:
        # Keep the raw reply visible. A fenced or chatty answer is why this failed.
        print(raw)
        return None
    return turns


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


def main() -> None:
    # source_text = load_pdf("sources/weathermaps.pdf")
    source_text = load_source("sources/weathermaps.pdf")
    # print(len(source_text))
    # print(source_text[:500])

    chunks = chunk_text(source_text)
    entries = []

    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1}/{len(chunks)} summarized")
        notes = make_notes(chunk)
        if notes is None:
            continue
        entries.append({"chunk": i, "notes": notes})

    with open("notes.json", "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(entries)} chunks to notes.json")
    if entries:
        min_turns, max_turns = turn_range(entries)
        print(f"Notes support {min_turns} to {max_turns} turns")

    # text_from_pdf = ""
    # try:
    #     text_from_pdf = load_pdf("blank.pdf")
    # except ValueError as err:
    #     print(err)

    # response = client.responses.create(
    #     model="grok-4.7",
    #     input=f"{prompt}\n\nSource paragraph:\n{paragraph}",
    #     )   

    # raw = response.output_text
    # try:
    #     turns = json.loads(raw)

    # except json.JSONDecodeError:
    #     print(raw)
        
    # list_of_notes = make_notes(chunks)
    # try:
    #     # turns = json.loads(list_of_notes)
    #     errors = validate_notes(list_of_notes)

    # except:
        
    # else:
    #     # print(validate_script(turns))
    #     # errors = validate_script(turns)
    #     # print(turns)
    #     audio_files = []
    #     if errors:
    #         print(errors)
    #     else:
    #         for i, turn in enumerate(turns):
    #             text = turn["text"]
    #             if turn["speaker"] == "HOST_A":
    #                 voice_id = "eve"
    #             else:
    #                 voice_id = "ara"
    #             path = f"turn_{i:02d}.mp3"
    #             audio_files.append(path)
    #             speak(text, voice_id, path)

    #         #audio was generated, let's put them into one file w pauses
    #         audio(audio_files)


def check_turn_range() -> None:
    """Length follows distinct notes. Repeats from chunk overlap do not add turns."""
    assert turn_range([]) == (6, 7)

    four = [{"chunk": 0, "notes": ["a", "b", "c", "d"]}]
    assert turn_range(four) == (6, 7)

    repeated = [
        {"chunk": 0, "notes": ["same fact", "other fact"]},
        {"chunk": 1, "notes": ["same fact"]},
    ]
    assert turn_range(repeated) == (6, 7)

    fifteen = [{"chunk": 0, "notes": [f"note {i}" for i in range(15)]}]
    assert turn_range(fifteen) == (17, 24)

    many = [{"chunk": 0, "notes": [f"note {i}" for i in range(40)]}]
    assert turn_range(many) == (18, 24)


def check_chunk_text() -> None:
    """The five chunk_text checks from milestone 2. A failed assert stops main."""
    assert chunk_text("") == []

    short = "Photosynthesis is how plants turn light into food."
    assert chunk_text(short) == [short]

    size, overlap = 3000, 300
    long_text = ("Plants store sugar. " * 600)[:10000]
    chunks = chunk_text(long_text, size, overlap)
    assert all(len(chunk) <= size for chunk in chunks)
    assert all(
        nxt.startswith(prev[-overlap:])
        for prev, nxt in zip(chunks, chunks[1:])
    )
    rebuilt = chunks[0] + "".join(chunk[overlap:] for chunk in chunks[1:])
    assert rebuilt == long_text


def check_make_notes() -> None:
    """make_notes sends one chunk and returns the parsed JSON list.

    The model is replaced with a fake reply, so these checks do not call xAI.
    """
    from unittest.mock import MagicMock, patch

    chunk = "Chlorophyll in the leaves absorbs light. That energy splits water."
    good = [
        "Chlorophyll absorbs light.",
        "The light is absorbed in the leaves.",
        "That energy splits water.",
    ]
    fake = MagicMock()
    fake.output_text = json.dumps(good)

    with patch.object(client.responses, "create", return_value=fake) as create:
        notes = make_notes(chunk)

    assert notes == good
    # Locks the map to grok-4.3. A later edit that puts chunk calls back
    # on grok-4.7 fails here before it spends the higher text rate.
    assert create.call_args.kwargs["model"] == "grok-4.3"
    sent = create.call_args.kwargs["input"]
    assert chunk in sent
    assert "3 to 6" in sent

    bad = MagicMock()
    bad.output_text = "not json"
    with patch.object(client.responses, "create", return_value=bad):
        # A reply that is not JSON is printed and not returned as notes.
        assert make_notes(chunk) is None


if __name__ == "__main__":
    check_chunk_text()
    check_turn_range()
    check_make_notes()
    main()