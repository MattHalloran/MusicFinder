#Grabs user settings from text files
from os import path

KEYS_PATH = 'api-keys.txt'
DIRECTORIES_PATH = 'directories.txt'

#Used for accessing various services
GENIUS_KEY = ''
YOUTUBE_KEY = ''

#Used for organizing data
INPUT_PATH = ''
SONG_DIRECTORY = ''
ALBUM_COVER_DIRECTORY = ''
LOG_DIRECTORY = ''

#Find keys
with open(KEYS_PATH) as f:
    lines = f.readlines()
    for line in lines:
        if 'GENIUS_KEY' in line:
            GENIUS_KEY = str.strip(line[len('GENIUS_KEY')+1:])
        elif 'YOUTUBE_KEY' in line:
            YOUTUBE_KEY = str.strip(line[len('YOUTUBE_KEY')+1:])

#Find inputs/outputs
with open(DIRECTORIES_PATH) as f:
    lines = f.readlines()
    for line in lines:
        if 'INPUT_PATH' in line:
            INPUT_PATH = path.expanduser(str.strip(line[len('INPUT_PATH')+1:]))
        elif 'SONG_DIRECTORY' in line:
            SONG_DIRECTORY = path.expanduser(str.strip(line[len('SONG_DIRECTORY')+1:]))
        elif 'ALBUM_COVER_DIRECTORY' in line:
            ALBUM_COVER_DIRECTORY = path.expanduser(str.strip(line[len('ALBUM_COVER_DIRECTORY')+1:]))
        elif 'LOG_DIRECTORY' in line:
            LOG_DIRECTORY = path.expanduser(str.strip(line[len('LOG_DIRECTORY')+1:]))