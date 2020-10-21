
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
import datetime
from checkMeta import checkMetaFile

from globals import INPUT_PATH, SONG_DIRECTORY, ALBUM_COVER_DIRECTORY, LOG_DIRECTORY
from utils import slugify, removeTitleJunk, words_kept_in_parens1
from genius import find_genius_data

sys.path.append(os.path.join(os.path.dirname(__file__), 'PyLyricsLocal'))

fileName = ''
ext = ''
artist = ''
title = ''


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

    openParenPos = title.find('(')
    closeParenPos = title.find(')')
    # If there are parentheses
    if openParenPos > 0 and closeParenPos > openParenPos:
        # Add space before open parenthesis
        if title[openParenPos-1] != ' ':
            title = title.replace('(', ' (')

        # Change all variations of featuring to feat.
        old_paren_text = title[openParenPos+1:closeParenPos]
        new_paren_text = str.strip(old_paren_text)
        if len(new_paren_text) > 0:
            if new_paren_text.startswith('FEAT'):
                new_paren_text = 'feat' + new_paren_text[len('FEAT'):]
            elif new_paren_text.lower().startswith('featuring'):
                new_paren_text = 'feat' + new_paren_text[len('featuring'):]
            elif new_paren_text.lower().startswith('with'):
                new_paren_text = 'feat' + new_paren_text[len('with'):]
            title = title.replace(old_paren_text, new_paren_text)

    feat_index = title.lower().find('feat')
    if feat_index > 0 and '(' not in title:
        title = title[:feat_index] + '(' + title[feat_index:] + ')'

    if '(feat' in title.lower() and '(feat.' not in title.lower():
        title.replace('(feat', '(feat.').replace('(FEAT', '(feat.')

    return title


# Attempts to add the following ID3 tags to the mp3 file:
# 1) artist - known
# 2) title - known
# 3) lyrics - parses from Genius
# 4) album name - parses from Genius
# 5) album art - uses findAlbumArt.py
def updateMetadata():
    # Create mutagen object
    meta = ID3(f'{fileName}.mp3')

    # Add known metadata
    meta.add(TPE1(encoding=3, text=artist))  # artist
    meta.add(TPE2(encoding=3, text=artist))  # album artist
    meta.add(TIT2(encoding=3, text=title))  # title

    # Add lyrics and album name from Genius
    genius_data = find_genius_data(removeTitleJunk(title, words_kept_in_parens1), artist)
    lyrics = genius_data("lyrics", None)
    default_album_name = f'{title} - Single'
    album_name = genius_data("album_name", default_album_name)
    if lyrics:
        meta.add(USLT(encoding=3, lang=u'eng', desc=u'desc', text=lyrics))  # lyrics
    meta.add(TALB(encoding=3, text=album_name))  # album name

    album_art_downloaded = False
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
    with open(INPUT_PATH) as f:
        lines = f.readlines()
        for line in lines:
            arguments = line.split(' - ')
            artist = str.strip(arguments[0])
            title = str.strip(formatTitle(arguments[1]))
            tempFileName = f'{SONG_DIRECTORY}/{slugify(artist)} - {slugify(title)}'
            if os.path.exists(f'{tempFileName}.mp3'):
                logMessage(f'{line} already exists. Skipping')
                continue
            youtube_url = syt.youtube_search(artist, removeTitleJunk(title, words_kept_in_parens1))
            ydl_opts = {
                'format': 'bestaudio/best',
                'nocheckcertificate': 'True',
                'outtmpl': f'{tempFileName}.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                    }],
            }
            if youtube_url is None:
                logMessage(f'Could not find youtube link for {line}')
                continue
            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtube_url])
                    updateMetadata()
                    (included, issues) = checkMetaFile(tempFileName)
                    if not issues:
                        albumName = TALB(included['TALB'])
                        finalFileName = f'{SONG_DIRECTORY}/{slugify(artist)}/{slugify(albumName)}/{slugify(title)}'
                        os.makedirs(finalFileName, exist_ok=True)
                        os.rename(tempFileName, finalFileName)

            except Exception as e:
                logMessage(f'Failed downloading {line}')
                print(e)


if __name__ == "__main__":
    main()
    print('done')
