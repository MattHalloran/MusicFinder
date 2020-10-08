#!/usr/bin/env python3

# requires: selenium, chromium-driver, retry
# Heavily inspired by http://sam.aiki.info/b/google-images.py

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import selenium.common.exceptions as sel_ex
import sys
import urllib.parse
from retry import retry
import logging

from sacad.cover import CoverSourceQuality, CoverSourceResult
from sacad.sources.base import CoverSource

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger()
retry_logger = None

css_thumbnail = "img.Q4LuWd"
css_large = "img.n3VNCb"
css_load_more = ".mye4qd"
selenium_exceptions = (sel_ex.ElementClickInterceptedException, sel_ex.ElementNotInteractableException, sel_ex.StaleElementReferenceException)

SAFE_SEARCH = "off"
NUM_IMAGES = 10
OPTS = ""  # e.g. isz:lt,islt:svga,itp:photo,ic:color,ift:jpg


class GoogleImagesWebScrapeCoverSource(CoverSource):
    """
    Cover source that scrapes Google Images search result pages.

    Google Image Search JSON API is not used because it is deprecated and Google
    is very agressively rate limiting its access.
    """

    BASE_URL = "https://www.google.com/images"

    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                         min_delay_between_accesses=2 / 3,
                         jitter_range_ms=(0, 600),
                         **kwargs)

    def getSearchUrl(self, album, artist):
        ''' See parent's def '''
        query = f'"{artist}" "{album}" album cover'
        opts = urllib.parse.quote(OPTS)
        search_url = f'https://www.google.com/search?safe={SAFE_SEARCH}&site=&tbm=isch&source=hp&q={query}&oq={query}&gs_l=img&tbs={opts}'
        return search_url

    def updateHttpHeaders(self, headers):
        """ parent's def """
        headers["User-Agent"] = self.ua.firefox

    def scroll_to_end(wd):
        wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    @retry(exceptions=KeyError, tries=6, delay=0.1, backoff=2, logger=retry_logger)
    def get_thumbnails(wd, want_more_than=0):
        wd.execute_script("document.querySelector('{}').click();".format(css_load_more))
        thumbnails = wd.find_elements_by_css_selector(css_thumbnail)
        n_results = len(thumbnails)
        if n_results <= want_more_than:
            raise KeyError("no new thumbnails")
        return thumbnails

    @retry(exceptions=KeyError, tries=6, delay=0.1, backoff=2, logger=retry_logger)
    def get_image_src(wd):
        actual_images = wd.find_elements_by_css_selector(css_large)
        sources = []
        for img in actual_images:
            src = img.get_attribute("src")
            if src.startswith("http") and not src.startswith("https://encrypted-tbn0.gstatic.com/"):
                sources.append(src)
        if not len(sources):
            raise KeyError("no large image")
        return sources

    @retry(exceptions=selenium_exceptions, tries=6, delay=0.1, backoff=2, logger=retry_logger)
    def retry_click(el):
        el.click()

    def get_images(wd, start=0, n=20, out=None):
        thumbnails = []
        count = len(thumbnails)
        while count < n:
            __class__.scroll_to_end(wd)
            try:
                thumbnails = __class__.get_thumbnails(wd, want_more_than=count)
            except KeyError:
                logger.warning("cannot load enough thumbnails")
                break
            count = len(thumbnails)
        sources = []
        for tn in thumbnails:
            try:
                __class__.retry_click(tn)
            except selenium_exceptions:
                logger.warning("main image click failed")
                continue
            sources1 = []
            try:
                sources1 = __class__.get_image_src(wd)
            except KeyError:
                pass
                # logger.warning("main image not found")
            if not sources1:
                tn_src = tn.get_attribute("src")
                if not tn_src.startswith("data"):
                    logger.warning("no src found for main image, using thumbnail")          
                    sources1 = [tn_src]
                else:
                    logger.warning("no src found for main image, thumbnail is a data URL")
            for src in sources1:
                if not src in sources:
                    sources.append(src)
                    if out:
                        print(src, file=out)
                        out.flush()
            if len(sources) >= n:
                break
        return sources

    # Overrides base fetchResults, since google image parsing uses a headless browser
    async def fetchResults(self, url, post_data=None):
        opts = Options()
        opts.add_argument("--headless")
        with webdriver.Chrome(ChromeDriverManager().install(), options=opts) as wd:
            wd.get(url)
            sources = __class__.get_images(wd, n=NUM_IMAGES, out=sys.stdout)
        return (None, sources)

    async def parseResults(self, api_data):
        """ See parent's def """
        results = []
        for rank, url in enumerate(api_data, 1):
            results.append(CoverSourceResult(url, CoverSourceQuality.NORMAL, rank))
        return results
