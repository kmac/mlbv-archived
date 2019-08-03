"""
Streaming functions
"""

import logging
import os
import subprocess

from datetime import datetime
from datetime import timezone
from dateutil import parser

import mlbv.mlbam.common.config as config
import mlbv.mlbam.common.util as util


LOG = logging.getLogger(__name__)


def _has_game_started(start_time_utc):
    return start_time_utc.replace(timezone.utc) < datetime.now(timezone.utc)


def _get_resolution():
    """Workaround for Issue #12
    If resolution is 'best' then change it to '720p_alt'
    See https://github.com/streamlink/streamlink/issues/1048
    """
    resolution = config.CONFIG.parser.get('resolution', '720p_alt')
    if 'best' in resolution:
        resolution = resolution.replace('best', '720p_alt')
        LOG.info("Workaround for issue #12: resolution 'best' is manually converted: %s", resolution)
    return resolution


def _uniquify_fetch_filename(fetch_filename, strategy='date'):
    if os.path.exists(fetch_filename):
        # don't overwrite existing file - use a new name based on hour,minute
        fetch_filename_orig = fetch_filename
        if strategy == 'index':
            index = 1
            fsplit = os.path.splitext(fetch_filename_orig)
            while os.path.exists(fetch_filename):
                index += 1
                fetch_filename = '{}-{}{}'.format(fsplit[0], index, fsplit[1])
        else:
            fsplit = os.path.splitext(fetch_filename)
            fetch_filename = '{}-{}{}'.format(fsplit[0], datetime.strftime(datetime.today(), "%H%M"), fsplit[1])
        LOG.info('File %s exists, using %s instead', fetch_filename_orig, fetch_filename)
    return fetch_filename


def get_fetch_filename(date_str, home_abbrev, away_abbrev, feedtype, fetch):
    if fetch:
        suffix = 'ts'
        if feedtype is None:
            fetch_filename = '{}-{}-{}.{}'.format(date_str, away_abbrev, home_abbrev, suffix)
        else:
            if feedtype in ('recap', 'condensed', ):
                suffix = 'mp4'
            fetch_filename = '{}-{}-{}-{}.{}'.format(date_str, away_abbrev, home_abbrev, feedtype, suffix)
        return _uniquify_fetch_filename(fetch_filename, strategy='index')
    return None


def play_highlight(playback_url, fetch_filename, is_multi_highlight=False):
    video_player = config.CONFIG.parser['video_player']
    if (fetch_filename is None or fetch_filename != '') \
            and not config.CONFIG.parser.getboolean('streamlink_highlights', True):
        cmd = [video_player, playback_url]
        LOG.info('Playing highlight: %s', str(cmd))
        subprocess.run(cmd)
    else:
        streamlink_highlight(playback_url, fetch_filename, is_multi_highlight)


def streamlink_highlight(playback_url, fetch_filename, is_multi_highlight=False):
    video_player = config.CONFIG.parser['video_player']
    streamlink_cmd = ["streamlink", ]

    # Issue 22: support extra streamlink parameters, like --player-external-http
    streamlink_extra_args = config.CONFIG.parser['streamlink_extra_args']
    if streamlink_extra_args:
        LOG.debug('Using streamlink_extra_args: %s', streamlink_extra_args)
        streamlink_cmd.extend([s.strip() for s in streamlink_extra_args.split(',')])
    else:
        # the --playe-no-close is required so it doesn't shut things down
        # prematurely after the stream is fully fetched
        streamlink_cmd.append("--player-no-close")
    if fetch_filename:
        streamlink_cmd.append("--output")
        streamlink_cmd.append(fetch_filename)
    elif video_player:
        LOG.debug('Using video_player: %s', video_player)
        if is_multi_highlight:
            if video_player == 'mpv':
                video_player += " --keep-open=no"
        streamlink_cmd.append("--player")
        streamlink_cmd.append(video_player)
        if config.CONFIG.parser.getboolean('streamlink_passthrough_highlights', True):
            streamlink_cmd.append("--player-passthrough=hls")
    if config.VERBOSE:
        streamlink_cmd.append("--loglevel")
        streamlink_cmd.append("debug")
    streamlink_cmd.append(playback_url)
    streamlink_cmd.append(_get_resolution())

    LOG.info('Playing highlight via streamlink: %s', str(streamlink_cmd))
    subprocess.run(streamlink_cmd)


def streamlink(stream_url, mlb_session, fetch_filename=None, from_start=False, offset=None):
    LOG.debug("Stream url: " + stream_url)
    # media_auth_cookie_str = access_token
    # user_agent_hdr = 'User-Agent=' + config.CONFIG.ua_iphone
    user_agent_hdr = 'User-Agent=' + config.CONFIG.ua_pc

    video_player = config.CONFIG.parser['video_player']
    streamlink_cmd = ["streamlink",
                      "--http-no-ssl-verify",
                      "--http-cookie", "Authorization=" + mlb_session.access_token,
                      "--http-header", user_agent_hdr,
                      "--hls-timeout", "600",         # default: 60
                      "--hls-segment-timeout", "60"]  # default: 10
    if from_start:
        streamlink_cmd.append("--hls-live-restart")
        LOG.info("Starting from beginning [--hls-live-restart]")
    elif offset:
        streamlink_cmd.append("--hls-start-offset")
        streamlink_cmd.append(offset)
        LOG.debug("Using --hls-start-offset %s", offset)

    # Issue 22: support extra streamlink parameters, like --player-external-http
    streamlink_extra_args = config.CONFIG.parser['streamlink_extra_args']
    if streamlink_extra_args:
        LOG.debug('Using streamlink_extra_args: %s', streamlink_extra_args)
        streamlink_cmd.extend([s.strip() for s in streamlink_extra_args.split(',')])
    else:
        # the --playe-no-close is required so it doesn't shut things down
        # prematurely after the stream is fully fetched
        streamlink_cmd.append("--player-no-close")
    if fetch_filename:
        fetch_filename = _uniquify_fetch_filename(fetch_filename)
        streamlink_cmd.append("--output")
        streamlink_cmd.append(fetch_filename)
    elif video_player:
        LOG.debug('Using video_player: %s', video_player)
        streamlink_cmd.append("--player")
        streamlink_cmd.append(video_player)
        if config.CONFIG.parser.getboolean('streamlink_passthrough', False):
            streamlink_cmd.append("--player-passthrough=hls")

    streamlink_hls_audio_select = config.CONFIG.parser['streamlink_hls_audio_select']
    if streamlink_hls_audio_select:
        streamlink_cmd.append("--hls-audio-select")
        streamlink_cmd.append(streamlink_hls_audio_select)
        if streamlink_hls_audio_select != '*':
            LOG.info('Including streamlink arg: --hls-audio-select=%s', streamlink_hls_audio_select)
    else:
        LOG.debug('Disabled streamlink --hls-audio-select')

    if config.VERBOSE:
        streamlink_cmd.append("--loglevel")
        streamlink_cmd.append("debug")
    streamlink_cmd.append(stream_url)
    streamlink_cmd.append(_get_resolution())

    LOG.debug('Playing: %s', str(streamlink_cmd))
    subprocess.run(streamlink_cmd)

    return streamlink_cmd


def play_audio(stream_url):
    # http://hlsaudio-akc.med2.med.nhl.com/ls04/nhl/2017/12/31/NHL_GAME_AUDIO_TORVGK_M2_VISIT_20171231_1513799214035/master_radio.m3u8
    pass
