
# Adds metadata from youtube-dl audio files.
# NOTE: youtube-dl code taken from https://github.com/ytdl-org/youtube-dl/issues/12225
# Author: Matt Halloran
# Version: 0.5.20200110

# TODO:
# 0. Finish
# 1. Skip files that already contain metadata

# Finds the best youtube link to download
import searchYoutube as syt
# youtube-dl imports (downloads song from url)
import youtube_dl
# used to add metadata to songs that's not already added by youtube-dl (album cover, album, lyrics)
from mutagen.id3 import ID3, APIC, USLT, TPE1, TPE2, TIT2, TALB
import findAlbumArt
# other imports
import sys
import os
import json
import traceback
import datetime
from checkMeta import checkMetaFile, checkMetaDir

from globals import INPUT_PATH, SONG_DIRECTORY, ALBUM_COVER_DIRECTORY, LOG_DIRECTORY
from utils import slugify, removeTitleJunk, words_kept_in_parens1
from genius import find_genius_data

sys.path.append(os.path.join(os.path.dirname(__file__), 'PyLyricsLocal'))


def logMessage(message: str):
    message = message.replace('\n', '')
    log_file = open(f'{LOG_DIRECTORY}/MusicFinderLogs.txt', "a")
    log_file.write(f'{datetime.datetime.now()} - {message}\n')
    log_file.close()


# Not perfect, but hopefully gets the job done
def formatTitle(title: str):
    title = str.strip(title)

    # Change [] to (), if there is not already a ()
    if '[' in title and '(' not in title:
        title = title.replace('[', '(').replace(']', ')')

    # Add parentheses around the features, if applicable
    feat_index = title.lower().find('feat')
    if feat_index > 0 and '(' not in title:
        title = title[:feat_index] + '(' + title[feat_index:] + ')'

    openParenPos = title.find('(')
    closeParenPos = title.find(')')
    # If there are parentheses
    if openParenPos > 0 and closeParenPos > openParenPos:
        # Add space before open parenthesis
        if title[openParenPos-1] != ' ':
            title = title.replace('(', ' (')

        # Change all variations of featuring to feat
        old_paren_text = title[openParenPos+1:closeParenPos]
        new_paren_text = str.strip(old_paren_text)
        if len(new_paren_text) > 0:
            # Case-insensitive featuring to feat
            if new_paren_text.lower().startswith('featuring'):
                new_paren_text = 'feat' + new_paren_text[len('featuring'):]
            # FEAT to feat
            elif new_paren_text.startswith('FEAT'):
                new_paren_text = 'feat' + new_paren_text[len('FEAT'):]
            # Case-insentivie with to feat
            elif new_paren_text.lower().startswith('with'):
                new_paren_text = 'feat' + new_paren_text[len('with'):]
            # Adding feat if not already there
            elif not new_paren_text.startswith('feat'):
                new_paren_text = 'feat ' + new_paren_text[:]
            title = title.replace(old_paren_text, new_paren_text)

    if '(feat' in title and '(feat.' not in title:
        title = title.replace('(feat', '(feat.')

    return title


# Downloads song using youtube-dl. Returns True if successful
def downloadSong(url: str, output_file: str):
    ydl_opts = {
        'format': 'bestaudio/best',
        'nocheckcertificate': 'True',
        'outtmpl': f'{output_file}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
            }],
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception:
        logMessage(f'Failed downloading {url}')
        print(traceback.format_exc())
        return False


# Attempts to add the following ID3 tags to the mp3 file:
# 1) artist - known
# 2) title - known
# 3) lyrics - parses from Genius
# 4) album name - parses from Genius
# 5) album art - uses findAlbumArt.py
def updateMetadata(fileName: str, artist: str, title: str):
    # Create mutagen object
    meta = ID3(f'{fileName}.mp3')

    # Add known metadata
    meta.add(TPE1(encoding=3, text=artist))  # artist
    meta.add(TPE2(encoding=3, text=artist))  # album artist
    meta.add(TIT2(encoding=3, text=title))  # title

    # Add lyrics and album name from Genius
    genius_data = find_genius_data(removeTitleJunk(title, words_kept_in_parens1), artist)
    lyrics = bool(genius_data) and genius_data["lyrics"]
    default_album_name = f'{title} - Single'
    album_name = bool(genius_data) and genius_data["album_name"]
    album_art_downloaded = False
    if lyrics:
        meta.add(USLT(encoding=3, lang=u'eng', desc=u'desc', text=lyrics))  # lyrics
    if album_name:
        meta.add(TALB(encoding=3, text=album_name))  # album name
        album_art_path = f'{ALBUM_COVER_DIRECTORY}/{slugify(artist)} - {slugify(album_name)}.png'
        # If album art has already been downloaded
        if os.path.exists(album_art_path):
            album_art_downloaded = True
        else:
            album_art_downloaded = findAlbumArt.downloadAlbumArt(album_name,
                                                                artist,
                                                                album_name == default_album_name)

    if album_art_downloaded:
        with open(album_art_path, 'rb') as albumart:
            meta.add(APIC(
                            encoding=3,
                            mime='image/png',
                            type=3, desc=u'Cover',
                            data=albumart.read()
                            ))

    meta.save(v2_version=3)


def main():
    # Grab all requested downloads from the input file
    with open(INPUT_PATH) as f:
        lines = f.readlines()
    failed_lines = []
    # Find existing songs with completed metadata, so they can be skipped
    dir_json = json.loads(checkMetaDir(SONG_DIRECTORY))
    completed_songs = [(x["artist"], x["title"]) for x in dir_json["goodFiles"]]
    for line in lines:
        # Parse artist and title from line
        arguments = line.split(' - ')
        artist = str.strip(arguments[0])
        title = str.strip(formatTitle(arguments[1]))
        if (artist, title) in completed_songs:
            logMessage(f'{line} completed file already exists. Skipping')
            continue
        # Create a temporary location to place the song
        tempFileName = f'{SONG_DIRECTORY}/{slugify(artist)} - {slugify(title)}'
        youtube_urls = syt.youtube_search(artist, removeTitleJunk(title, words_kept_in_parens1))
        if youtube_urls is None:
            logMessage(f'Could not find any youtube links for {line}')
            failed_lines.append(line)
            continue
        # Try youtube links until one works
        success = False
        for url in youtube_urls:
            success = downloadSong(url, tempFileName)
            if success:
                break
        if not success:
            failed_lines.append(line)
            continue
        try:
            updateMetadata(tempFileName, artist, title)
            (included, issues) = checkMetaFile(f'{tempFileName}.mp3')
            # If download and metadata is correct, move the file to a permanent location
            if not issues:
                albumName = TALB(included['TALB'])
                finalFileDir = f'{SONG_DIRECTORY}/{slugify(artist)}/{slugify(albumName)}'
                finalFileName = f'{finalFileDir}/{slugify(title)}.mp3'
                os.makedirs(finalFileDir, exist_ok=True)
                os.rename(f'{tempFileName}.mp3', finalFileName)
            else:
                failed_lines.append(line)

        except Exception:
            logMessage(f'Failed downloading {line}')
            failed_lines.append(line)
            print(traceback.format_exc())
    # Remove successful downloads from the input file
    with open(INPUT_PATH, 'w') as f:
        f.writelines(failed_lines)
        f.close()


if __name__ == "__main__":
    main()
    print('done')
