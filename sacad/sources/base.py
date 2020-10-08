import abc
import asyncio
import itertools
import logging
import operator
import os
import random
import string
import unicodedata
import urllib.parse

import appdirs
import fake_useragent
import web_cache

from sacad import http_helpers
from sacad.cover import CoverImageFormat, CoverSourceQuality


MAX_THUMBNAIL_SIZE = 256


class CoverSource(metaclass=abc.ABCMeta):

  """ Base class for all cover sources. """

  def __init__(self, target_size, size_tolerance_prct, *, min_delay_between_accesses=0, jitter_range_ms=None,
               rate_limited_domains=None, allow_cookies=False):
    self.target_size = target_size
    self.size_tolerance_prct = size_tolerance_prct
    self.logger = logging.getLogger(self.__class__.__name__)

    self.http = http_helpers.Http(allow_session_cookies=allow_cookies,
                                  min_delay_between_accesses=min_delay_between_accesses,
                                  jitter_range_ms=jitter_range_ms,
                                  rate_limited_domains=rate_limited_domains,
                                  logger=self.logger)

    ua_cache_dir = os.path.join(appdirs.user_cache_dir(appname="sacad",
                                                       appauthor=False),
                                "fake_useragent")
    os.makedirs(ua_cache_dir, exist_ok=True)
    self.ua = fake_useragent.UserAgent(path=os.path.join(ua_cache_dir, "ua.json"))

    if not hasattr(__class__, "api_cache"):
      db_filepath = os.path.join(appdirs.user_cache_dir(appname="sacad",
                                                        appauthor=False),
                                 "sacad-cache.sqlite")
      os.makedirs(os.path.dirname(db_filepath), exist_ok=True)
      day_s = 60 * 60 * 24
      __class__.api_cache = web_cache.WebCache(db_filepath,
                                               "cover_source_api_data",
                                               caching_strategy=web_cache.CachingStrategy.FIFO,
                                               expiration=random.randint(day_s * 7, day_s * 14),  # 1-2 weeks
                                               compression=web_cache.Compression.DEFLATE)
      __class__.probe_cache = web_cache.WebCache(db_filepath,
                                                 "cover_source_probe_data",
                                                 caching_strategy=web_cache.CachingStrategy.FIFO,
                                                 expiration=day_s * 30 * 6)  # 6 months
      logging.getLogger('Cache').debug(f'Total size of file {db_filepath}: {__class__.api_cache.getDatabaseFileSize()}')
      for cache, cache_name in zip((__class__.api_cache, __class__.probe_cache),
                                   ('cover_source_api_data', 'cover_source_probe_data')):
        purged_count = cache.purge()
        logging.getLogger('Cache').debug(f'{purged_count} obsolete entries have been removed from cache {cache_name}')
        row_count = len(cache)
        logging.getLogger('Cache').debug(f'Cache {cache_name} contains {row_count} entries')

  async def closeSession(self):
    """ Closes HTTP session to make aiohttp happy. """
    await self.http.close()

  async def search(self, album, artist):
    """ Search for a given album/artist and return an iterable of CoverSourceResult. """
    print(f"Searching with source '{self.__class__.__name__}'...")
    album = self.processAlbumString(album)
    artist = self.processArtistString(artist)
    url_data = self.getSearchUrl(album, artist)
    if isinstance(url_data, tuple):
      url, post_data = url_data
    else:
      url = url_data
      post_data = None
    try:
      store_in_cache_callback, api_data = await self.fetchResults(url, post_data)
      print('going to parse results')
      results = await self.parseResults(api_data)
    except Exception as e:
      # raise
      print(f'Search with source "{self.__class__.__name__}" failed: {e.__class__.__qualname__} {e}')
      return ()
    else:
      if results and store_in_cache_callback:
        # only store in cache if parsing succeeds and we have results
        await store_in_cache_callback()

    return results

  async def fetchResults(self, url, post_data=None):
    """ Get a (store in cache callback, search results) tuple from an URL. """
    if post_data is not None:
      print(f'Querying URL {url} {dict(post_data)}...')
    else:
      print(f'Querying URL {url}...')
    headers = {}
    self.updateHttpHeaders(headers)
    return await self.http.query(url,
                                 post_data=post_data,
                                 headers=headers,
                                 cache=__class__.api_cache)

  async def probeUrl(self, url, response_headers=None):
    """ Probe URL reachability from cache or HEAD request. """
    self.logger.debug(f'Probing URL {url}...')
    headers = {}
    self.updateHttpHeaders(headers)
    resp_headers = {}
    resp_ok = await self.http.isReachable(url,
                                          headers=headers,
                                          response_headers=resp_headers,
                                          cache=__class__.probe_cache)

    if response_headers is not None:
      response_headers.update(resp_headers)

    return resp_ok

  @staticmethod
  def assembleUrl(base_url, params):
    """ Build an URL from URL base and parameters. """
    print('in assembleUrl')
    print(f'{base_url}?{urllib.parse.urlencode(params)}')
    return f'{base_url}?{urllib.parse.urlencode(params)}'

  @staticmethod
  def unaccentuate(s):
    """ Replace accentuated chars in string by their non accentuated equivalent. """
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

  @staticmethod
  def unpunctuate(s, *, char_blacklist=string.punctuation):
    """ Remove punctuation from string s. """
    # remove punctuation
    s = "".join(c for c in s if c not in char_blacklist)
    # remove consecutive spaces
    return " ".join(filter(None, s.split(" ")))

  def processArtistString(self, artist):
    """ Process artist string before building query URL. """
    return __class__.unpunctuate(artist.lower())

  def processAlbumString(self, album):
    """ Process album string before building query URL. """
    return __class__.unpunctuate(album.lower())

  @abc.abstractmethod
  def getSearchUrl(self, album, artist):
    """
    Build a search results URL from an album and/or artist name.

    If the URL must be accessed with an HTTP GET request, return the URL as a string.
    If the URL must be accessed with an HTTP POST request, return a tuple with:
    - the URL as a string
    - the post parameters as a collections.OrderedDict

    """
    pass

  def updateHttpHeaders(self, headers):
    """ Add API specific HTTP headers. """
    pass

  @abc.abstractmethod
  async def parseResults(self, api_data):
    """ Parse API data and return an iterable of results. """
    pass
