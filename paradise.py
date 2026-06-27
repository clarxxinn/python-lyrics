import time
import sys

print("\n\n")

lyrics = [
    ("And she walks down", 1.22, 0.10),
    ("I noticed how she does it for real now", 3.57, 0.08),
    ("And she talks loud", 0.50, 0.13),
    ("She's telling me what I wanna hear now, is it real now", 1.13, 0.10),
    ("", 0, 0),
    ("She calls me in the middle of a Sunday nights", 0.35, 0.09),
    ("I'm falling just a little baby, shit ain't right", 0.35, 0.09),
    ("She calls me in the middle of a Sunday night", 0.35, 0.09),
    ("I'm falling just a little baby, shit ain't right", 1.12, 0.09),
]

def type_out(text, char_delay=0.1):
    for char in text: 
        sys.stdout.write(char) 
        sys.stdout.flush()
        time.sleep(char_delay)
    sys.stdout.write("\n")
    sys.stdout.flush()

def play_lyrics(lyrics):
    for line, line_delay, char_delay in lyrics:
        type_out(line, char_delay)
        time.sleep(line_delay)

if __name__ == "__main__":
    play_lyrics(lyrics)