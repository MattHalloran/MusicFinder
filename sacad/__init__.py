""" Smart Automatic Cover Art Downloader : search and download music album covers. """

__version__ = "2.2.3"
__author__ = "desbma"
__license__ = "MPL 2.0"

import argparse
import asyncio
import functools
import logging
import os
from sacad import hash
from sacad import sources
from sacad.cover import CoverSourceResult, HAS_JPEGOPTIM, HAS_OPTIPNG, SUPPORTED_IMG_FORMATS


async def search_and_download(album, artist, format, size, out_filepath, *, size_tolerance_prct, amazon_tlds, use_google_images):
  """ Search and download a cover, return True if success, False instead. """
  # register sources
  source_args = (size, size_tolerance_prct)
  cover_sources = [sources.LastFmCoverSource(*source_args),
                   sources.AmazonCdCoverSource(*source_args),
                   sources.AmazonDigitalCoverSource(*source_args)]
  #Find album urls from Amazon
  for tld in amazon_tlds:
    cover_sources.append(sources.AmazonCdCoverSource(*source_args, tld=tld))
  #Find album urls from Google
  if use_google_images:
    cover_sources.append(sources.GoogleImagesWebScrapeCoverSource(*source_args))

  # schedule search work
  search_futures = []
  for cover_source in cover_sources:
    coroutine = cover_source.search(album, artist)
    future = asyncio.ensure_future(coroutine)
    search_futures.append(future)

  # wait for it
  await asyncio.wait(search_futures)

  # get results (doesn't download the images yet)
  results = []
  for future in search_futures:
    source_results = future.result()
    results.extend(source_results)

  # Remove bad results (currently just album covers that aren't square)
  results = await CoverSourceResult.preProcessForComparison(results, size, size_tolerance_prct)
  # Sort results
  results.sort(reverse=True,
               key=functools.cmp_to_key(functools.partial(CoverSourceResult.compare,
                                                          target_size=size,
                                                          size_tolerance_prct=size_tolerance_prct)))
  if not results:
    logging.getLogger("Main").info("No results")

  # Download some of the albums
  done = False
  #temp = []
  hashes = []
  num_downloaded = 0
  for result in results:
    if num_downloaded >= 20:
      break
    try:
      await result.download(format, size, size_tolerance_prct)
      hashes.append(result.get_image_hash())
      #temp.append(result)
      num_downloaded += 1
    except Exception as e:
      logging.getLogger('Main').warning(f'Download of {result} failed: {e.__class__.__qualname__} {e}')
      
  #for t in temp:
  #  t.get_image().save(os.path.expanduser(f'~/Music/Albums/{t.get_image_hash()}.{t.get_image().format}'))

  # If there is a duplicate cover, pick the highest quality version of that as the final cover. Otherwise, pick the first
  if num_downloaded > 0:
    best_hash = max(set(hashes), key = hashes.count)
    results = [r for r in results if r.get_image_hash() == best_hash]
    results.sort(key=lambda r: r.size, reverse=True)
    results[0].get_image().save(out_filepath)
    done = True

  # cleanup sessions
  close_cr = []
  for cover_source in cover_sources:
    close_cr.append(cover_source.closeSession())
  await asyncio.gather(*close_cr)

  return done


def setup_common_args(arg_parser):
  arg_parser.add_argument("-t",
                          "--size-tolerance",
                          type=int,
                          default=25,
                          dest="size_tolerance_prct",
                          help="""Tolerate this percentage of size difference with the target size.
                                  Note that covers with size above or close to the target size will still be preferred
                                  if available""")
  arg_parser.add_argument("-a",
                          "--amazon-sites",
                          nargs="+",
                          choices=sources.AmazonCdCoverSource.TLDS[1:],
                          default=(),
                          dest="amazon_tlds",
                          help="""Amazon site TLDs to use as search source, in addition to amazon.com""")
  arg_parser.add_argument("-d",
                          "--disable-low-quality-sources",
                          action="store_true",
                          default=False,
                          dest="use_google_images",
                          help="""Enable searching Google Images. May find obscure results, but is slower and less reliable.""")
