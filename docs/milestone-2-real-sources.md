# Milestone 2: Real Sources

**Goal:** Point the CLI at a PDF, a web page, or a notes file, and get back an episode about that material, even when the source is too long for a single prompt.

**Done for the whole milestone:** `python main.py --source some_chapter.pdf` produces `episode.mp3`, and every turn in it is grounded in the source.

## The big idea (read this first)

Milestone 1 sent one short paragraph straight to Grok. Real sources are longer, so a new question comes up: how do we turn a long document into one 5-minute conversation?

- **"Retrieval" (RAG)** finds the few chunks that best answer a *question*. That is perfect later for interactive mode ("Hosts, what does chapter 3 say about X?").
- **An overview episode has no question.** It needs to *cover* the whole source. So here we use **map-reduce** instead:
  1. **Map:** turn each chunk into a few short, factual study notes.
  2. **Reduce:** write the two-host script from all the notes together.

Self-check: in one sentence each, explain why plain retrieval would give a *worse* overview episode, and when retrieval *will* be the right tool. (Answer at the bottom.)

---

## Step 1: Read a PDF into text  *(line by line)*

- Install `pypdf` (`pip install pypdf`).
- Write `load_pdf(path) -> str`, which opens the PDF with `pypdf.PdfReader`, pulls text from each page, and joins the pages with blank lines.
- Check its docs for the exact method names: https://pypdf.readthedocs.io

**Done when:** `print(len(load_pdf("test.pdf")))` prints a sensible character count, and printing the first 500 characters shows readable text.
**Watch for:** scanned PDFs (pictures of pages) return little or no text. Detect this. If the text is nearly empty, return a clear error rather than an empty episode.

## Step 2: Read a web page and a notes file  *(vibe code, then read it)*

- Web pages: let Cursor write `load_url(url) -> str` using `requests` plus a main-text extractor such as `trafilatura` or `beautifulsoup4`. Then read every line and make sure you can explain it.
- Notes: `load_text(path) -> str` is just reading a `.txt` or `.md` file.
- Write `load_source(source) -> str`, which picks the right loader based on whether the source is a URL or ends in `.pdf`, `.txt`, or `.md`. Write this part yourself, line by line.

**Done when:** all three source types return clean text, and an unsupported type (like `.docx`) gives a friendly error.

## Step 3: Chunk the text  *(line by line, a core skill)*

- Write `chunk_text(text, size=3000, overlap=300) -> list[str]`, which counts in characters.
- Each chunk starts `size - overlap` characters after the previous one, so neighbors share a little text and no idea gets cut in half without context.
- Bonus: move each split point back to the nearest paragraph break or sentence end, so chunks don't stop mid-word.

**Self-checking tests (write these first):**
- `chunk_text("", ...)` returns `[]`.
- A text shorter than `size` returns exactly one chunk, equal to the text.
- For a 10,000-character text, every chunk is at most `size` long.
- The end of each chunk overlaps the start of the next.
- Joining the chunks while removing the overlaps rebuilds the original text (or at least, no characters are lost).

**Done when:** all five tests pass.

## Step 4: Map, turning each chunk into study notes  *(line by line)*

- Write a prompt that turns one chunk into 3 to 6 short bullet notes, using only facts stated in the chunk.
- Ask for JSON (a list of strings), and write a tiny validator the same way you did in milestone 1.
- Save the notes to `notes.json` so you can inspect them, and so reruns don't pay for the same calls twice.

**Done when:** a 10-page PDF produces a notes file you can read and agree with, and each note can be traced back to its chunk.

## Step 5: Reduce, writing the script from the notes  *(line by line)*

- Reuse your milestone 1 script prompt, but feed it the combined notes instead of a raw paragraph.
- Raise the turn limit (for example, 12 to 20 turns) and update `validate_script` to take `min_turns` and `max_turns` arguments instead of hardcoding 6 to 10.
- If the combined notes are still very long, that's a sign to reduce in two rounds (notes of notes). Only build that if you actually hit the problem.

**Done when:** the script passes validation three runs in a row on your test PDF.

## Step 6: One command, end to end  *(vibe code the CLI, keep the pipeline yours)*

- Let Cursor scaffold `main.py` with `argparse`: `--source`, `--out` (default `episode.mp3`), and `--minutes` (an optional target length).
- The pipeline is `load_source`, then `chunk_text`, then the map, then the reduce, then `validate_script`, then TTS, then stitching. Wire this together yourself.
- Print simple progress lines, like `Chunk 3/12 summarized`.

**Done when:** one command turns a real PDF into a playable `episode.mp3`.

## Step 7: A first grounding check  *(line by line, a mini-eval)*

- For 5 random turns, ask Grok as a judge: "Is every factual claim in this line supported by these source notes? Answer yes or no, plus the unsupported claim if there is one."
- Print a score, for example `5/5 grounded`.
- This is the seed of your eval harness, the same idea as True Reports.

**Done when:** you can run the check and get a score, and you've read at least one "no" case (if any came up) to see why.

---

## Costs (check, don't guess)

- Map-reduce makes one Grok call per chunk, plus one for the script. Before running big files, check current token prices on the xAI console's pricing page, and log each call's usage numbers (the API response includes token usage) so you can calculate the real cost per episode.
- TTS was listed at $15 per million characters on xAI's voice overview page as of Oct 2026. Recheck it before you trust it for pricing decisions.

## Self-check answers

- Retrieval only returns the chunks that match a query. With no question, it would skip big parts of the source, and the episode would miss things.
- Retrieval is right when there *is* a question, such as interactive mode, or "make an episode only about topic X from this textbook."
