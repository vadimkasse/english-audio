# english-audio

CLI tool to extract audio clips from video by matching phrases in SRT subtitles.

## Features

- matches phrases within single or contiguous subtitle blocks
- ignores punctuation, line breaks, and subtitle formatting differences
- uses subtitle timings to cut audio from the first matched block to the last
- interactive CLI: enter phrase, choose match, name the output file
- exports clips as mp3
- reveals the created file in Finder on macOS

## Usage

audio

Workflow:
1. Paste the phrase
2. Press Enter twice to finish input
3. Choose a match if multiple matches are found
4. Enter output filename
5. Get the mp3 clip

## Requirements

- Python 3.9+
- ffmpeg
- macOS (for Finder reveal)

## Notes

- works best with accurate SRT subtitles
- matches only contiguous subtitle blocks
- does not assemble fragments from unrelated parts of the file