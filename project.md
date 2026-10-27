# study-pod — Project Context

## What this is
A personal study-podcast app: upload sources (PDF, web page, notes), and an LLM writes a
two-host conversation that explains the material (Host A explains, Host B asks questions).
Each host is voiced by a different TTS voice, and the clips are stitched into one MP3.
Inspired by NotebookLM's audio overviews but uses the xAI Grok API. Must NOT copy
NotebookLM's name, branding, or UI.

Doubles as a portfolio project for Applied AI / AI Engineer roles, so code should be
clean, readable, and well-tested.

## Roadmap
1. Python CLI prototype (current phase)
2. Later: source ingestion (PDF/web), chunking + retrieval (RAG) for large sources
3. Later: post-episode quiz with spaced repetition (missed questions resurface; poor
   scores suggest re-listening to the relevant episode moment)
4. Later: interactive mode where the user joins and asks the hosts questions
   (likely LangGraph)
5. Later: packaged SwiftUI Mac/iPhone app, possibly a niche subscription
   (e.g., homeschool study aids or certification exam prep)

## Milestone 1: "Hello, two hosts"
Hardcoded paragraph of notes in -> ~60-second two-voice episode.mp3 out. No PDFs/RAG yet.
1. Setup: venv, .env with XAI_API_KEY, .gitignore excluding .env
2. First Grok call: send paragraph, print reply
3. Script as JSON: list of {"speaker": "HOST_A" | "HOST_B", "text": "..."}, 6–10 turns,
   validated (both speakers present, alternating, no empty turns)
4. TTS each turn with a distinct voice per host -> turn_00.mp3, turn_01.mp3, ...
5. Stitch clips with short pauses -> episode.mp3 (pydub + ffmpeg)

## Stack
- Python 3.11+, packages: openai, requests, python-dotenv, pydub
- System: ffmpeg
- LLM: xAI Responses API via the OpenAI SDK with base_url="https://api.x.ai/v1",
  model "grok-4.7"
- TTS: xAI POST https://api.x.ai/v1/tts with JSON {text, voice_id, language};
  returns MP3 bytes by default. Built-in voices include "eve" and "ara".
  Supports speech tags like [pause], [laugh]. Max 60,000 chars per request.
- Docs: https://docs.x.ai/docs/overview,
  https://docs.x.ai/developers/model-capabilities/audio/text-to-speech

## How to help me (important)
- I'm refreshing Python and learning by hand. I write CORE LOGIC myself, line by line:
  chunking/retrieval, the script-writing prompt and Grok call, TTS calls, audio
  stitching, and evals. For these, explain, review, and hint. Don't write the full
  solution unless I ask.
- Vibe-coding is fine for boilerplate, setup, config, CLI scaffolding, and UI.
- Keep changes small and scoped to the current milestone step.
- Never invent API parameters, model names, prices, or terms. If unsure, say so and
  point me to the docs.
- Never hardcode or print API keys; read them from .env.

## About me
I know Swift/SwiftUI and have built a RAG system in LangGraph with an eval harness.
I learn best with short explanations and self-checking exercises.