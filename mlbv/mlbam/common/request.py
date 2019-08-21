"""
Handle HTTP requests

This is a small wrapper around requests/json, with support for some very rudimentary caching.
"""

import json
import logging
import os
import sys
import time

import requests

import mlbv.mlbam.common.config as config
import mlbv.mlbam.common.util as util


LOG = logging.getLogger(__name__)

CACHE = dict()
MAX_CACHE_FILENAME_LEN = 250

# These values are used to control the stale times on cached data.
# Values in seconds:
CACHE_NEVER = 0
CACHE_SHORT = 60
CACHE_HOUR = 60 * 60
CACHE_DAY = 24 * CACHE_HOUR
CACHE_FOREVER = sys.maxsize


def _get_cache_stale_secs(cache_stale=None):
    # overrides config
    caching_val = config.CONFIG.parser.get('cache', 'normal')
    if caching_val in ('never', 'false', 'False', 'off', 'Off'):
        return 0
    if caching_val in ('test', 'forever'):
        return CACHE_FOREVER
    if cache_stale is None:
        return 0
    return cache_stale


def _get_cachedir():
    cachedir = os.path.join(util.get_tempdir(), 'cache')
    if not os.path.exists(cachedir):
        LOG.debug('Creating cache directory: ' + cachedir)
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)
    return cachedir


def request_json(url, output_filename=None, cache_stale=None):
    """Sends a request expecting a json-formatted response.
    If output_filename is given, then the output is saved to file.
    This also enables basic caching, where cache_stale is the number of seconds
    since file is last modified before the cached file is considered stale (0 means disable the cache).
    """
    cache_stale = _get_cache_stale_secs(cache_stale)
    # Guard against very long filenames:
    if output_filename and len(output_filename) >= MAX_CACHE_FILENAME_LEN:
        output_filename = output_filename[0:MAX_CACHE_FILENAME_LEN-1]
    if output_filename and cache_stale:
        if output_filename in CACHE:
            return CACHE[output_filename]
        json_file = os.path.join(_get_cachedir(), '{}.json'.format(output_filename))
        if os.path.exists(json_file) and (int(time.time()) - os.path.getmtime(json_file) < cache_stale):
            with open(json_file) as jfh:
                CACHE[output_filename] = json.load(jfh)
            if config.DEBUG:
                LOG.info('Loaded from cache: %s', output_filename)
            return CACHE[output_filename]

    LOG.debug('Getting url=%s ...', url)
    headers = {
        'User-Agent': config.CONFIG.ua_iphone,
        'Connection': 'close'
    }
    util.log_http(url, 'get', headers, sys._getframe().f_code.co_name)
    response = requests.get(url, headers=headers, verify=config.VERIFY_SSL)
    response.raise_for_status()

    # Note: this fails on windows in some cases https://github.com/kennethreitz/requests-html/issues/171
    if output_filename is not None or (config.DEBUG and config.SAVE_JSON_FILE):
        json_file = os.path.join(_get_cachedir(), '{}.json'.format(output_filename))
        with open(json_file, 'w', encoding='utf-8') as out:  # write date to json_file
            out.write(response.text)
    if cache_stale:
        LOG.debug('Caching url=%s, filename=%s', url, output_filename)
        CACHE[output_filename] = response.json()
        return CACHE[output_filename]
    return response.json()
