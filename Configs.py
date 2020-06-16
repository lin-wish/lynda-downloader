import os
import pathlib
import urllib

LYNDA_COOKIES = os.path.join(
    str(pathlib.Path(__file__).resolve().parent), 'cookies.txt')

DOWNLOAD_DIR = os.path.join(
    str(pathlib.Path(__file__).resolve().parent), 'lynda')

MAX_WORKERS = 6

BASE_URL = 'https://www.lynda.com'
