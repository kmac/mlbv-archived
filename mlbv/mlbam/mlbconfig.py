import configparser
import inspect
import logging
import os
import sys

import mlbv.mlbam.common.config as config

LOG = logging.getLogger(__name__)


DEFAULTS = {  # is applied to initial config before reading from file - these are the defaults:
    'mlbv': {
        'username': '',
        'password': '',
        'favs': '',
        'fav_colour': 'blue',
        'scores': 'true',
        'use_short_feeds': 'true',
        'filter': '',
        'cdn': 'akamai',
        'resolution': '720p_alt',
        'video_player': 'mpv',
        'api_url': 'https://statsapi.mlb.com',
        'playback_scenario': 'HTTP_CLOUD_WIRED_60',  # mp4Avc, hlsCloud, HTTP_CLOUD_WIRED, HTTP_CLOUD_WIRED_60, highBit
        'streamlink_highlights': 'true',  # if false will send url direct to video_player (no resolution selection)
        'streamlink_passthrough_highlights': 'true',  # allows seeking
        'streamlink_passthrough': 'false',
        'streamlink_hls_audio_select': '*',
        'streamlink_extra_args': '',
        'stream_start_offset_secs': str(config.DEFAULT_STREAM_START_OFFSET_SECS),
        'audio_player': 'mpv',
        'debug': 'false',
        'verbose': 'false',
        'game_critical_colour': 'yellow',
        'verify_ssl': 'true',
        'save_json_file_by_timestamp': 'false',
        'unicode': 'true',
    }
}
