"""
Streaming functions
"""

import logging
import os
import requests
import subprocess
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

from datetime import datetime
from dateutil import tz

import mlbam.config as config
import mlbam.util as util


LOG = logging.getLogger(__name__)


def _has_game_started(start_time_utc):
    return start_time_utc.replace(tzinfo=tz.tzutc()) < datetime.now(tz.tzutc())


def select_feed_for_team(game_rec, team_code, feedtype=None):
    found = False
    if game_rec['away']['abbrev'] == team_code:
        found = True
        if feedtype is None and 'away' in game_rec['feed']:
            feedtype = 'away'  # assume user wants their team's feed
    elif game_rec['home']['abbrev'] == team_code:
        found = True
        if feedtype is None and 'home' in game_rec['feed']:
            feedtype = 'home'  # assume user wants their team's feed
    if found:
        if feedtype is None:
            LOG.info('Default (home/away) feed not found: choosing first available feed')
            if len(game_rec['feed']) > 0:
                feedtype = list(game_rec['feed'].keys())[0]
                LOG.info("Chose '{}' feed (override with --feed option)".format(feedtype))
        if feedtype not in game_rec['feed']:
            LOG.error("Feed is not available: {}".format(feedtype))
            return None, None
        return game_rec['feed'][feedtype]['mediaPlaybackId'], game_rec['feed'][feedtype]['eventId']
    return None, None


def find_highlight_url_for_team(game_rec, feedtype):
    if feedtype not in config.HIGHLIGHT_FEEDTYPES:
        raise Exception('highlight: feedtype must be condensed or recap')
    if feedtype in game_rec['feed'] and 'playback_url' in game_rec['feed'][feedtype]:
        return game_rec['feed'][feedtype]['playback_url']
    LOG.error('No playback_url found for {} vs {}'.format(game_rec['away']['abbrev'], game_rec['home']['abbrev']))
    return None


def play_stream(game_data, team_to_play, feedtype, date_str, fetch, wait_for_start):
    game_rec = None
    for game_pk in game_data:
        if team_to_play in (game_data[game_pk]['away']['abbrev'], game_data[game_pk]['home']['abbrev']):
            game_rec = game_data[game_pk]
            break
    if game_rec is None:
        util.die("No game found for team {}".format(team_to_play))

    if feedtype is not None and feedtype in config.HIGHLIGHT_FEEDTYPES:
        # handle condensed/recap
        playback_url = find_highlight_url_for_team(game_rec, feedtype)
        if playback_url is None:
            util.die("No playback url for feed '{}'".format(feedtype))
        play_highlight(playback_url, get_fetch_filename(date_str, game_rec, feedtype, fetch))
    else:
        # handle full game (live or archive)
        # this is the only feature requiring an authenticated session
        import mlbam.session as session
        mlb_session = session.MLBSession()

        if wait_for_start and not _has_game_started(game_rec['mlbdate']):
            LOG.info('Waiting for game to start. Local start time is ' + util.convert_time_to_local(game_rec['mlbdate']))
            print('Use Ctrl-c to quit .', end='', flush=True)
            count = 0
            while not _has_game_started(game_rec['mlbdate']):
                time.sleep(10)
                count += 1
                if count % 6 == 0:
                    print('.', end='', flush=True)

        media_playback_id, event_id = select_feed_for_team(game_rec, team_to_play, feedtype)
        if media_playback_id is not None:
            stream_url = mlb_session.lookup_stream_url(game_rec['game_pk'], media_playback_id)
            if stream_url is not None:
                if config.DEBUG:
                    mlb_session.save_playlist_to_file(stream_url)
                streamlink(stream_url, mlb_session, get_fetch_filename(date_str, game_rec, feedtype, fetch))
            else:
                LOG.error("No stream URL")
        else:
            LOG.info("No game found for {}".format(team_to_play))
    return 0


def get_fetch_filename(date_str, game_rec, feedtype, fetch):
    if fetch:
        if feedtype is None:
            return '{}-{}-{}.mp4'.format(date_str, game_rec['away']['abbrev'], game_rec['home']['abbrev'])
        else:
            return '{}-{}-{}-{}.mp4'.format(date_str, game_rec['away']['abbrev'], game_rec['home']['abbrev'], feedtype)
    return None


def play_highlight(playback_url, fetch_filename):
    video_player = config.CONFIG.parser['video_player']
    if (fetch_filename is None or fetch_filename != '') \
            and not config.CONFIG.parser.getboolean('streamlink_highlights', True):
        cmd = [video_player, playback_url]
        LOG.info('Playing highlight: ' + str(cmd))
        subprocess.run(cmd)
    else:
        streamlink_highlight(playback_url, fetch_filename)


def streamlink_highlight(playback_url, fetch_filename):
    video_player = config.CONFIG.parser['video_player']
    streamlink_cmd = ["streamlink", "--player-no-close", ]
    if fetch_filename is not None:
        streamlink_cmd.append("--output")
        streamlink_cmd.append(fetch_filename)
    elif video_player is not None and video_player != '':
        LOG.debug('Using video_player: {}'.format(video_player))
        streamlink_cmd.append("--player")
        streamlink_cmd.append(video_player)
    if config.CONFIG.parser.getboolean('streamlink_passthrough_highlights', True):
        streamlink_cmd.append("--player-passthrough=hls")
    if config.VERBOSE:
        streamlink_cmd.append("--loglevel")
        streamlink_cmd.append("debug")
    streamlink_cmd.append(playback_url)
    streamlink_cmd.append(config.CONFIG.parser.get('resolution', 'best'))

    LOG.info('Playing highlight via streamlink: ' + str(streamlink_cmd))
    subprocess.run(streamlink_cmd)


def streamlink(stream_url, mlb_session, fetch_filename=None):
    LOG.debug("Stream url: " + stream_url)
    auth_cookie_str = "Authorization=" + mlb_session.access_token
    # media_auth_cookie_str = access_token
    #user_agent_hdr = 'User-Agent=' + config.CONFIG.ua_iphone
    user_agent_hdr = 'User-Agent=' + config.CONFIG.ua_pc

    video_player = config.CONFIG.parser['video_player']
    streamlink_cmd = ["streamlink",
                      "--http-no-ssl-verify",
                      "--player-no-close",
                      "--http-header", user_agent_hdr,
                      "--http-cookie", auth_cookie_str]
                      # "--http-cookie", media_auth_cookie_str,

    # include our cookies
    cookie_dict = mlb_session.get_cookie_dict()
    for cookie_name in cookie_dict:
        streamlink_cmd.append("--http-cookie")
        streamlink_cmd.append('{}={}'.format(cookie_name, cookie_dict[cookie_name]))

    if fetch_filename is not None:
        if os.path.exists(fetch_filename):
            # don't overwrite existing file - use a new name based on hour,minute
            fetch_filename_orig = fetch_filename
            fsplit = os.path.splitext(fetch_filename)
            fetch_filename = '{}-{}{}'.format(fsplit[0], datetime.strftime(datetime.today(), "%H%m"), fsplit[1])
            LOG.info('File {} exists, using {} instead'.format(fetch_filename_orig, fetch_filename))
        streamlink_cmd.append("--output")
        streamlink_cmd.append(fetch_filename)
    elif video_player is not None and video_player != '':
        LOG.debug('Using video_player: {}'.format(video_player))
        streamlink_cmd.append("--player")
        streamlink_cmd.append(video_player)
        if config.CONFIG.parser.getboolean('streamlink_passthrough', False):
            streamlink_cmd.append("--player-passthrough=hls")
    if config.VERBOSE:
        streamlink_cmd.append("--loglevel")
        streamlink_cmd.append("debug")
    streamlink_cmd.append(stream_url)
    streamlink_cmd.append(config.CONFIG.parser.get('resolution', 'best'))

    LOG.debug('Playing: ' + str(streamlink_cmd))
    subprocess.run(streamlink_cmd)

    return streamlink_cmd


def play_audio(stream_url):
    # http://hlsaudio-akc.med2.med.nhl.com/ls04/nhl/2017/12/31/NHL_GAME_AUDIO_TORVGK_M2_VISIT_20171231_1513799214035/master_radio.m3u8
    pass
