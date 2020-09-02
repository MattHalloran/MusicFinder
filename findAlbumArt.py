#Local copy of sacad. Downloaded from: https://github.com/desbma/sacad
import sacad
from sacad.cover import CoverImageFormat
from sacad.sources import AmazonCdCoverSource, GoogleImagesWebScrapeCoverSource
import asyncio
from os import path
from utils import slugify

#Finds and downloads album art 
def downloadAlbumArt(album:str, artist:str):
    try:
        success = asyncio.get_event_loop().run_until_complete(sacad.search_and_download(album, #Album name
                                artist, #Artist name
                                CoverImageFormat.PNG, #File format, or None if you don't care
                                1024, #Preferred album size
                                path.expanduser(f'~/Music/Albums/{slugify(artist)} - {slugify(album)}.png'), #Output path
                                size_tolerance_prct=25,
                                amazon_tlds=AmazonCdCoverSource.TLDS[:],
                                use_google_images=True))
    except Exception as e:
        print(f'ERROR! findAlbumArt.py - downloadAlbumArt. Passed in album: {album}, artist: {artist}. Error: {e}')
    return success
