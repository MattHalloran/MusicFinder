
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
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC
import findAlbumArt
# other imports
import sys
import os

# Used to grab data from Genius. See https://dev.to/willamesoares/how-to-integrate-spotify-and-genius-api-to-easily-crawl-song-lyrics-with-python-4o62 and https://stackoverflow.com/questions/13137817/how-to-download-image-using-requests
import requests
import shutil
# Used to crawl webpage
from bs4 import BeautifulSoup

from globals import GENIUS_KEY, INPUT_PATH, SONG_DIRECTORY, ALBUM_COVER_DIRECTORY
from utils import slugify, removeTitleJunk, excludes_list1

sys.path.append(os.path.join(os.path.dirname(__file__), 'PyLyricsLocal'))

fileName = ''
ext = ''
artist = ''
title = ''


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

    if '(feat' in title.lower() and not '(feat.' in title.lower():
        title.replace('(feat', '(feat.').replace('(FEAT', '(feat.')

    return title


# Attempts to add the following ID3 tags to the mp3 file:
# 1) artist - known
# 2) title - known
# 3) lyrics - parses from Genius
# 4) album name - parses from Genius
# 5) album art - uses findAlbumArt.py
def updateMetadata():
    # Create meta object
    meta = None
    try:
        meta = EasyID3(f'{fileName}.mp3')
    except mutagen.id3.ID3NoHeaderError:
        meta = mutagen.File(fileName, easy=True)
        meta.add_tags()

    # Add known metadata
    meta['artist'] = artist
    meta['albumartist'] = artist
    meta['title'] = title

    # Search Genius for the correct song url
    # Uses authentication token, which can be made at https://genius.com/api-clients
    def request_song_url(song_title, artist_name):
        base_url = 'https://api.genius.com'
        headers = {'Authorization': 'Bearer ' + GENIUS_KEY}
        search_url = base_url + '/search'
        data = {'q': song_title + ' ' + artist_name}
        response = requests.get(search_url, data=data, headers=headers)
        json = response.json()

        remote_song_info = None
        try:
            for hit in json['response']['hits']:
                if artist.lower() in hit['result']['primary_artist']['name'].lower():
                    remote_song_info = hit
                    break
        except KeyError:
            print('ERROR: Used wrong Genius authentication key!!!!!!!')

        if remote_song_info:
            return remote_song_info['result']['url']
        return remote_song_info

    album_name = f'{title} - Single'
    is_single = True
    # Find song url
    song_url = request_song_url(removeTitleJunk(title, excludes_list1), artist)
    # Get page data TODO: if lyrics not found, album is not set I think? This can probably be grabbed in the album cover code
    if song_url is not None:
        page = requests.get(song_url)
        soup = BeautifulSoup(page.text, 'html.parser')

        meta['lyricist'] = (str.strip(soup.find('div', class_='lyrics').text))

        # This album art is too small to use in the metadata, but
        # we can use its hash when searching for a larger one
        album_info_div = soup.find('div', class_='header_with_cover_art-primary_info').text
        album_index = album_info_div.find('Album')
        if album_index != -1:
            album_name = str.strip(album_info_div[album_index+5:])
            is_single = False
    meta['album'] = album_name

    album_art_downloaded = False
    album_art_path = f'{ALBUM_COVER_DIRECTORY}/{slugify(artist)} - {slugify(album_name)}.png'
    # If album art has already been downloaded
    if os.path.exists(album_art_path):
        album_art_downloaded = True
    # Tries to download art using findAlbumArt.py first
    else:
        album_art_downloaded = findAlbumArt.downloadAlbumArt(album_name, artist, is_single)

    if not album_art_downloaded:
        album_art_div = soup.find('div', class_='header_with_cover_art')
        img_tag = album_art_div.find_all('img')
        if len(img_tag) > 0:
            img_src = img_tag[0]['src']
            response = requests.get(img_src, stream=True)
            with open(album_art_path, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
            del response
            album_art_downloaded = True

    meta.save()
    meta = ID3(f'{fileName}.mp3')

    if album_art_downloaded:
        with open(album_art_path, 'rb') as albumart:
            meta['APIC'] = APIC(
                            encoding=3,
                            mime='image/png',
                            type=3, desc=u'Cover',
                            data=albumart.read()
                            )

    meta.save()


with open(INPUT_PATH) as f:
    lines = f.readlines()
    searchParams = [line.split(' - ') for line in lines]
    for search in searchParams:
        artist = str.strip(search[0])
        title = str.strip(formatTitle(search[1]))
        fileName = f'{SONG_DIRECTORY}/{slugify(artist)} - {slugify(title)}'
        youtube_url = f'https://www.youtube.com/watch?v={syt.youtube_search(artist, removeTitleJunk(title, excludes_list1))}'
        ydl_opts = {
            'format': 'bestaudio/best',
            'nocheckcertificate': 'True',
            'outtmpl': f'{fileName}.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
                }],
        }
        if youtube_url is None:
            continue
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
                updateMetadata()
        except Exception as e:
            print(e)


print('done')
