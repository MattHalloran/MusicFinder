from __future__ import annotations
import asyncio
import enum
import imghdr
import io
import itertools
import logging
import math
import mimetypes
import operator
import os
import pickle
import shutil
import urllib.parse
from PIL import Image
import requests
import mimetypes

import appdirs
import bitarray
import PIL.Image
import PIL.ImageFile
import PIL.ImageFilter
import numpy as np
import web_cache

from sacad import mkstemp_ctx
from enum import Enum

class CoverImageFormat(Enum):
  JPEG = 1
  PNG = 2

class CoverSourceQuality(Enum):
  LOW = 1
  NORMAL = 2
  HIGH = 3

class CoverImageMetadata(Enum):
  NONE = 1
  FORMAT = 2
  SIZE = 3
  ALL = 4

HAS_JPEGOPTIM = shutil.which("jpegoptim") is not None
HAS_OPTIPNG = shutil.which("optipng") is not None
SUPPORTED_IMG_FORMATS = {'jpg': CoverImageFormat.JPEG,
                         'jpeg': CoverImageFormat.JPEG,
                         'png': CoverImageFormat.PNG}


def is_square(x):
  """ Return True if integer x is a perfect square, False otherwise. """
  return math.sqrt(x).is_integer()


class CoverSourceResult:
  """ Cover image returned by a source, candidate to be downloaded. """

  METADATA_PEEK_SIZE_INCREMENT = 2 ** 12
  MAX_FILE_METADATA_PEEK_SIZE = 20 * METADATA_PEEK_SIZE_INCREMENT
  IMG_SIG_SIZE = 16

  def __init__(self, url:str, quality:CoverSourceQuality, rank=None):
    """
    Args:
      url: url that image came from
      quality: CoverSourceQuality enum. Relates to how much you trust the source
      rank: If from Google Images, for example, the first image would be rank 1
    """
    self.url = url
    self.quality = quality
    self.rank = rank
    response = requests.get(url)
    content_type = response.headers['content-type']
    extension = mimetypes.guess_extension(content_type)
    self.format = SUPPORTED_IMG_FORMATS.get(extension[1:], None)
    self.image = Image.open(io.BytesIO(response.content))
    self.width, self.height = self.image.size
    self.image_hash = self.average_hash(self.image)


  def __str__(self):
    return f'url:{self.url}, width:{self.width}, height:{self.height}'
  
  def get_image(self):
    return self.image

  @staticmethod
  def compare(first, second, *, target_size, size_tolerance_prct):
    """
    Compare cover relevance/quality.

    Return -1 if first is a worst match than second, 1 otherwise, or 0 if cover can't be discriminated.

    This code is responsible for comparing two cover results to identify the best one, and is used to sort all results.
    It is probably the most important piece of code of this tool.
    Covers with sizes under the target size (+- configured tolerance) are excluded before comparison.
    The following factors are used in order:
      1. Prefer approximately square covers
      2. Prefer size above target size
      3. If both below target size, prefer closest
      4. Prefer covers of most reliable source
      5. Prefer best ranked cover
    If all previous factors do not allow sorting of two results (very unlikely):
      6. Prefer covers having the target size
      7. Prefer PNG covers
      8. Prefer exactly square covers

    We don't overload the __lt__ operator because we need to pass the target_size parameter.

    """
    for c in (first, second):
      assert(isinstance(c.width, int) and isinstance(c.height, int))

    # prefer square covers #1
    delta_ratio1 = abs(first.width / first.height - 1)
    delta_ratio2 = abs(second.width / second.height - 1)
    if abs(delta_ratio1 - delta_ratio2) > 0.15:
      return -1 if (delta_ratio1 > delta_ratio2) else 1

    # prefer size above preferred
    delta_size1 = ((first.width + first.height) / 2) - target_size
    delta_size2 = ((second.width + second.height) / 2) - target_size
    if (((delta_size1 < 0) and (delta_size2 >= 0)) or
            (delta_size1 >= 0) and (delta_size2 < 0)):
      return -1 if (delta_size1 < delta_size2) else 1

    # if both below target size, prefer closest
    if (delta_size1 < 0) and (delta_size2 < 0) and (delta_size1 != delta_size2):
      return -1 if (delta_size1 < delta_size2) else 1

    # prefer covers of most reliable source
    qs1 = first.quality.value
    qs2 = second.quality.value
    if qs1 != qs2:
      return -1 if (qs1 < qs2) else 1

    # prefer best ranked
    if ((first.rank is not None) and
            (second.rank is not None) and
            (first.__class__ is second.__class__) and
            (first.rank != second.rank)):
      return -1 if (first.rank > second.rank) else 1

    # prefer the preferred size
    if abs(delta_size1) != abs(delta_size2):
      return -1 if (abs(delta_size1) > abs(delta_size2)) else 1

    # prefer png
    if first.format != second.format:
      return -1 if (second.format is CoverImageFormat.PNG) else 1

    # prefer square covers #2
    if (delta_ratio1 != delta_ratio2):
      return -1 if (delta_ratio1 > delta_ratio2) else 1

    # fuck, they are the same!
    return 0

  @staticmethod
  async def preProcessForComparison(results:CoverSourceResult):
    """ Process results to prepare them for future comparison and sorting. """
    #Remove non-square images
    results = [r for r in results if r.width == r.height]
    return results

  @staticmethod
  def average_hash(image:PIL.Image, hash_size=8, mean=np.mean):
    """ Average hash implementation 
    Returns a string bit representation"""
    if hash_size < 2:
      raise ValueError("Hash size must be greater than or equal to 2")

    # reduce size and complexity, then covert to grayscale
    image = image.convert("L").resize((hash_size, hash_size), PIL.Image.ANTIALIAS)

    # find average pixel value; 'pixels' is an array of the pixel values, ranging from 0 (black) to 255 (white)
    pixels = np.asarray(image)
    avg = mean(pixels)

    # create string of bits
    diff = pixels > avg
    diff_as_string = ''.join(['1' if x else '0' for x in diff.flatten().tolist()])
    print(diff_as_string)
    return diff_as_string


# silence third party module loggers
logging.getLogger('PIL').setLevel(logging.ERROR)
