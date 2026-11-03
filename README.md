# study-pod

**In progress.** This is a command-line prototype, not a shipped app.

study-pod turns a source into a short two-host study episode. One host explains. The other asks the questions a learner would ask. Each host has its own voice, and the clips are stitched into one MP3. A grounding check then scores whether spoken lines stay inside the source, so the episode does not teach claims the material never made.

A run needs your own [xAI](https://docs.x.ai/docs/overview) API key. There is no hosted demo.

## Done

- Read a PDF, a web page, or a `.txt` / `.md` notes file
- Split a long source into overlapping chunks
- Map each chunk to short study notes, then write one script from all of the notes
- Reject a script that is the wrong shape: both hosts must speak, they must alternate, and no turn may be empty
- Voice the turns (`eve` and `ara`) and stitch them into one MP3
- Score five random lines against the notes and print a result such as `5/5 grounded`

## Next

- A quiz after the episode, with spaced repetition: missed questions come back, and a weak score points at the moment to hear again
- A mode where the learner joins the hosts and asks questions
- A SwiftUI app for Mac and iPhone, aimed at homeschool study or certification prep

## Run

Python 3.11+ and [ffmpeg](https://ffmpeg.org/) (pydub uses it to write MP3s).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Put your key in `.env` as `XAI_API_KEY=...`, then:

```bash
python main.py --source sources/sample-notes.md
```

That writes `episode.mp3` in this folder. `--out` changes the path. `--minutes` asks for a longer or shorter episode, capped by how many notes the source actually supports.

Generated audio, `notes.json`, and `script.json` stay on your machine. They are listed in `.gitignore`.
