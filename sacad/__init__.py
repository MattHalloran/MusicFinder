""" Smart Automatic Cover Art Downloader : search and download music album covers. """

__version__ = "2.2.3"
__author__ = "desbma"
__license__ = "MPL 2.0"

import asyncio
import functools
import logging
from sacad import sources
from sacad.cover import CoverSourceResult


async def search_and_download(album, artist, format, size, out_filepath, *, size_tolerance_prct, is_single):
    """ Search and download a cover, return True if success, False instead. """

    # Register sources. Each source is a different website (Amazon, Google Images, etc.)
    source_args = (size, size_tolerance_prct)
    # If a single, it's best to only use google images
    if is_single:
        cover_sources = [sources.GoogleImagesWebScrapeCoverSource(*source_args)]
    else:
        cover_sources = [sources.LastFmCoverSource(*source_args),
                         sources.AmazonDigitalCoverSource(*source_args)]

    # schedule search work
    search_futures = []
    for cover_source in cover_sources:
        coroutine = cover_source.search(album, artist)
        future = asyncio.ensure_future(coroutine)
        search_futures.append(future)

    # wait for it
    await asyncio.wait(search_futures)

    # get results
    results = []
    for future in search_futures:
        source_results = future.result()
        results.extend(source_results)

    # Remove bad results (currently just album covers that aren't square)
    results = await CoverSourceResult.preProcessForComparison(results)
    # Sort results
    results.sort(reverse=True,
                 key=functools.cmp_to_key(functools.partial(CoverSourceResult.compare,
                                                            target_size=size,
                                                            size_tolerance_prct=size_tolerance_prct)))   
    success = False
    # If there is a duplicate cover, pick the highest quality version of that as the final cover.
    # Otherwise, pick the first
    if len(results) > 0:
        hashes = [r.image_hash for r in results]
        best_hash = max(set(hashes), key=hashes.count)
        results = [r for r in results if r.image_hash == best_hash]
        results.sort(key=lambda r: r.width*r.height, reverse=True)
        results[0].get_image().save(out_filepath)
        success = True
    else:
        logging.getLogger("Main").info("No results")

    # cleanup sessions
    close_cr = []
    for cover_source in cover_sources:
        close_cr.append(cover_source.closeSession())
    await asyncio.gather(*close_cr)

    return success
