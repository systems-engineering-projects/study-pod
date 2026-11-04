Prep: 
On paper, 
write the exact JSON shape you want Grok to return.
Write three rules your check function will enforce.

[
  {"speaker": "HOST_A", "text": "So today we're talking about photosynthesis..."},
  {"speaker": "HOST_B", "text": "Wait, how does a plant actually eat light?"}
]

We need to check:
Structure checks are plain Python, fast and certain, and they belong in this step. Your "empty response" rule is one. Here are the ones I'd add:

The reply parses with json.loads and comes back as a list.
Every turn has exactly the keys speaker and text, and speaker is HOST_A or HOST_B.
No text is empty or only whitespace.

Both hosts speak, they alternate, and there are 6 to 10 turns.
Quality checks are about meaning, and these are your evals. Your "is it entailed" idea fits here: it means every claim is supported by the source. That's your True Reports skill, and it's a great portfolio piece. But it needs its own LLM-as-judge or entailment model, so let's save it for a later milestone and give it a proper eval harness. Profanity sits in between. A simple word-list check is easy, but a good prompt rarely produces profanity, so add it to the list for later. It will matter more once outside sources come in.

write `validate_script(turns)`. It should return a list of error strings, and an empty list means the script passed. Then test it by hand on two bad examples: one where `HOST_A` speaks twice in a row, and one with an empty `text`. You're done when both bad examples return errors and the good example above returns `[]`. Show me the code when you're done, and I'll review it before we write the prompt. 🧙

then:
Two-host script as structured data (line by line). This is the heart of the app. Write the prompt that makes Grok return a JSON list of turns like {"speaker": "HOST_A", "text": "..."}, with one host explaining and the other asking questions, in 6 to 10 turns. You're done when your code parses the reply with json.loads, and a small check function confirms that both speakers appear, they alternate, and no turn is empty.

**Next is the prompt, the second half of step 3, and you write it line by line.** A good script prompt tells Grok four things:

1. **Who the hosts are.** `HOST_A` explains, and `HOST_B` is curious and asks the questions a learner would ask.
2. **What to use.** Only the source paragraph, with no outside facts. This sets up your entailment evals later.
3. **The rules.** 6 to 10 turns, alternating, with each turn spoken aloud in one to three sentences.
4. **The output.** Only a JSON list in your exact shape, with no prose or code fences around it.

**Your exercise:** in `script.py`, write that prompt as a string. Send it with your photosynthesis paragraph, run `json.loads(response.output_text)`, and pass the result to `validate_script`. You're done when it prints `[]` on three runs in a row. If a run fails, save the raw reply so we can see why. xAI also offers [structured outputs](https://docs.x.ai/docs/overview), which force JSON. We'll try those after you've seen how far a plain prompt gets.

**Step 4 is voicing each turn, line by line.** Write `speak(text, voice_id, path)`. It should POST to `https://api.x.ai/v1/tts` with `text`, `voice_id` and `"language": "en"`, call `raise_for_status()`, and write `response.content` to `path`. Then loop over your validated turns. Use `eve` for `HOST_A` and `ara` for `HOST_B`, and save each turn as `turn_00.mp3`, `turn_01.mp3`, and so on. To get the zero-padded names, use `f"turn_{i:02d}.mp3"`.





**Now the last step of milestone 1, step 5: stitching the clips together, line by line.** With `pydub`, load each clip using `AudioSegment.from_mp3(path)`, and make a short silence with `AudioSegment.silent(duration=400)`. The duration is in milliseconds. Start with an empty `AudioSegment.empty()`, add each clip and then a silence, and save it all using `episode.export("episode.mp3", format="mp3")`. Be sure to loop over `sorted()` file names, which is exactly why you zero-padded them.