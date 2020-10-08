#Local copy of sacad. Downloaded from: https://github.com/desbma/sacad
import sacad
from sacad.sources import GoogleImagesWebScrapeCoverSource
import asyncio
from os import path
from utils import slugify

#Finds and downloads album art 
def downloadAlbumArt(album:str, artist:str, is_single:bool=False):
    try:
        if is_single:
            fileName = f'{slugify(artist)} - {slugify(album)} - Single'
        else:
            fileName = f'{slugify(artist)} - {slugify(album)}'
        success = asyncio.get_event_loop().run_until_complete(sacad.search_and_download(album, #Album name
                                artist, #Artist name
                                "png", #File format, or None if you don't care
                                1024, #Preferred album size
                                path.expanduser(f'~/Music/Albums/{fileName}.png'), #Output path
                                size_tolerance_prct=25,
                                is_single=is_single))
        return success
    except Exception as e:
        print(f'ERROR! findAlbumArt.py - downloadAlbumArt. Passed in album: {album}, artist: {artist}. Error: {e}')
        return False
