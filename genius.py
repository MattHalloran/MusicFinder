# Search Genius for the correct song url
# Uses authentication token, which can be made at https://genius.com/api-clients
# See See https://dev.to/willamesoares/how-to-integrate-spotify-and-genius-api-to-easily-crawl-song-lyrics-with-python-4o62
# and https://stackoverflow.com/questions/13137817/how-to-download-image-using-requests

from bs4 import BeautifulSoup
import requests
from globals import GENIUS_KEY
from utils import removeTitleJunk, words_kept_in_parens2, uncensor


def request_song_url(title: str, artist: str):
    base_url = 'https://api.genius.com'
    headers = {'Authorization': 'Bearer ' + GENIUS_KEY}
    search_url = base_url + '/search'
    data = {'q': title + ' ' + artist}
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


# Possible TODO find hash of album
def find_genius_data(title: str, artist: str):
    """ Returns all useful information that can be found on Genius.
    This is currently lyrics and album name """
    song_url = request_song_url(title, artist)
    # If normal title returns no results, try a simplified one
    if song_url is None:
        simpler_title = removeTitleJunk(title, words_kept_in_parens2)
        simpler_title = uncensor(simpler_title)
        song_url = request_song_url(simpler_title, artist)
        if song_url is None:
            return {}
    page = requests.get(song_url)
    soup = BeautifulSoup(page.text, 'html.parser')

    lyrics = str.strip(soup.find('div', class_='lyrics').text)
    album_name = None

    # This album art is too small to use in the metadata, but
    # we can use its hash when searching for a larger one
    album_info_div = soup.find('div', class_='header_with_cover_art-primary_info').text
    album_index = album_info_div.find('Album')
    if album_index != -1:
        album_name = str.strip(album_info_div[album_index+5:])

    return {"lyrics": lyrics,
            "album_name": album_name}
