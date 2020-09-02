# Original code based off of https://github.com/Jetsetter/dhash
# For more information, read https://www.pyimagesearch.com/2017/11/27/image-hashing-opencv-python/

import argparse
import time
import sys
from PIL import Image

def calculate_hash(image:Image, hashSize:int = 8):
    """Calculates a 2*hashSize*hashSize bit hash of a PIL image"""
    image_data = image.convert('L').resize((hashSize+1, hashSize+1)).getdata()
    width = hashSize+1
    row_hash = 0
    col_hash = 0
    for y in range(hashSize):
        for x in range(hashSize):
            offset = y * width + x
            row_bit = image_data[offset] < image_data[offset + 1]
            row_hash = row_hash << 1 | row_bit

            col_bit = image_data[offset] < image_data[offset + width]
            col_hash = col_hash << 1 | col_bit

    print(f'{row_hash}{col_hash}')
    return f'{row_hash}{col_hash}'