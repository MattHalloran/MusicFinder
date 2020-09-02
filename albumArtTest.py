#Local copy of sacad. Downloaded from: https://github.com/desbma/sacad
#TODO: removed reference thing from sacad that compares similar images. Replace functionality with hash string comparison
import sacad
from sacad.cover import CoverImageFormat
from sacad.sources import AmazonCdCoverSource, GoogleImagesWebScrapeCoverSource
import asyncio
from os import path

def downloadAlbumArt(album:str, artist:str):
    success = asyncio.get_event_loop().run_until_complete(sacad.search_and_download(album, #Album name
                              artist, #Artist name
                              CoverImageFormat.PNG, #File format, or None if you don't care
                              1024, #Preferred album size
                              path.expanduser(f'~/Music/Albums/{artist} - {album}.png'), #Output path
                              size_tolerance_prct=25,
                              amazon_tlds=AmazonCdCoverSource.TLDS[:],
                              use_google_images=True))
    return success

succeeded = downloadAlbumArt('ASTROWORLD', 'Travis Scott')
print('done')
