"""Now the last step of milestone 1, step 5: 
stitching the clips together, line by line. 
With pydub, load each clip using AudioSegment.from_mp3(path), 
and make a short silence with AudioSegment.silent(duration=400).
 The duration is in milliseconds. 
 Start with an empty AudioSegment.empty(), 
 add each clip and then a silence, 
 and save it all using 
 episode.export("episode.mp3", format="mp3"). 
 Be sure to loop over sorted() file names, 
 which is exactly why you zero-padded them."""

import pydub
from pydub import AudioSegment

def audio(audio_files) -> None:

    """input - audio_files - a list of the audio files
    output - one mp3 file called episode that has all the files plus pauses
    """


    episode = AudioSegment.empty()

    sorted_audio = sorted(audio_files)

    for file_name in sorted_audio:
        #load clip
        clip = AudioSegment.from_mp3(file_name)

        pause = AudioSegment.silent(duration=400)

        episode += clip
        episode += pause


    episode.export("episode.mp3", format="mp3")
