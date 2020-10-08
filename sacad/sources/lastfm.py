import collections
import string
import xml.etree.ElementTree

from sacad.cover import CoverSourceQuality, CoverSourceResult
from sacad.sources.base import CoverSource


class LastFmCoverSource(CoverSource):
    """
    Cover source using the official LastFM API.

    http://www.lastfm.fr/api/show?service=290
    """

    BASE_URL = "https://ws.audioscrobbler.com/2.0/"
    API_KEY = "2410a53db5c7490d0f50c100a020f359"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, min_delay_between_accesses=0.1, **kwargs)

    def getSearchUrl(self, album, artist):
        """ See parent's def """
        payload = {"method": "album.getinfo",
                   "api_key": __class__.API_KEY,
                   "album": album,
                   "artist": artist}
        return (__class__.BASE_URL, payload)

    @staticmethod
    def unpunctuate(self, s):
        """ See parent's def """
        # Use same blacklist as usual, minus ' and &
        print('in the child unpunctuate')
        char_blacklist = set(string.punctuation)
        char_blacklist.remove("'")
        char_blacklist.remove("&")
        char_blacklist = frozenset(char_blacklist)
        return self().unpunctuate(s.lower(), char_blacklist=char_blacklist)

    async def parseResults(self, api_data):
        """ See parent's def """
        results = []

        # get xml results list
        xml_root = xml.etree.ElementTree.fromstring(api_data)
        status = xml_root.get("status")
        if status != "ok":
            raise Exception("Unexpected Last.fm response status: %s" % (status))
        img_elements = xml_root.findall("album/image")

        for img_element in img_elements:
            img_url = img_element.text
            if img_url:
                results.append(CoverSourceResult(img_url, CoverSourceQuality.NORMAL))

        return results
