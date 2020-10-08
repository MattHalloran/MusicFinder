import abc
import logging
import os
import random
import string
import requests

import appdirs
import fake_useragent
import web_cache

from sacad import http_helpers


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
        (url, post_data) = self.getSearchUrl(album, artist)
        try:
            api_data = await self.fetchResults(url, post_data)
            print('going to parse results')
            results = await self.parseResults(api_data)
        except Exception as e:
            print(f'Search with source "{self.__class__.__name__}" failed: {e.__class__.__qualname__} {e}')
            return ()

        return results

    async def fetchResults(self, url, post_data=None):
        """ Get search results from the url and post_data """
        req = None
        if post_data:
            req = requests.post(url, data=post_data)
        else:
            req = requests.post(url)
        return req.text

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
