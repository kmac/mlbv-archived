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

import mlbam.auth as auth
import mlbam.util as util
import mlbam.config as config


LOG = logging.getLogger(__name__)


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


def fetch_stream(game_pk, content_id, event_id, get_session_key_func):
    """ game_pk: game_pk
        event_id: eventId
        content_id: mediaPlaybackId
    """
    stream_url = None
    media_auth = None

    auth_cookie = auth.get_auth_cookie()
    if auth_cookie is None:
        LOG.error("fetch_stream: not logged in")
        return stream_url, media_auth

    session_key = get_session_key_func(game_pk, event_id, content_id, auth_cookie)
    if session_key is None:
        return stream_url, media_auth
    elif session_key == 'blackout':
        msg = ('The game you are trying to access is not currently available due to local '
               'or national blackout restrictions.\n'
               ' Full game archives will be available 48 hours after completion of this game.')
        LOG.info('Game Blacked Out: {}'.format(msg))
        return stream_url, media_auth

    url = config.CONFIG.mf_svc_url
    url += '?contentId=' + content_id
    url += '&playbackScenario=' + config.CONFIG.playback_scenario
    url += '&platform=' + config.CONFIG.platform
    url += '&sessionKey=' + urllib.parse.quote_plus(session_key)

    # Get user set CDN
    if config.CONFIG.parser['cdn'] == 'akamai':
        url += '&cdnName=MED2_AKAMAI_SECURE'
    elif config.CONFIG.parser['cdn'] == 'level3':
        url += '&cdnName=MED2_LEVEL3_SECURE'

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
        "Authorization": auth_cookie,
        "User-Agent": config.CONFIG.svc_user_agent,
        "Proxy-Connection": "keep-alive"
    }

    util.log_http(url, 'get', headers, sys._getframe().f_code.co_name)
    req = requests.get(url, headers=headers, cookies=auth.load_cookies(), verify=config.VERIFY_SSL)
    json_source = req.json()

    if json_source['status_code'] == 1:
        media_item = json_source['user_verified_event'][0]['user_verified_content'][0]['user_verified_media_item'][0]
        if media_item['blackout_status']['status'] == 'BlackedOutStatus':
            msg = ('The game you are trying to access is not currently available due to local '
                   'or national blackout restrictions.\n'
                   'Full game archives will be available 48 hours after completion of this game.')
            util.die('Game Blacked Out: {}'.format(msg))
        elif media_item['auth_status'] == 'NotAuthorizedStatus':
            msg = 'You do not have an active subscription. To access this content please purchase a subscription.'
            util.die('Account Not Authorized: {}'.format(msg))
        else:
            stream_url = media_item['url']
            media_auth = '{}={}'.format(str(json_source['session_info']['sessionAttributes'][0]['attributeName']),
                                        str(json_source['session_info']['sessionAttributes'][0]['attributeValue']))
            session_key = json_source['session_key']
            auth.update_session_key(session_key)
    else:
        msg = json_source['status_message']
        util.die('Error Fetching Stream: {}', msg)

    LOG.debug('fetch_stream stream_url: ' + stream_url)
    LOG.debug('fetch_stream media_auth: ' + media_auth)
    return stream_url, media_auth


def save_playlist_to_file(stream_url, media_auth):
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
        "User-Agent": config.CONFIG.svc_user_agent,
        "Cookie": media_auth
    }
    util.log_http(stream_url, 'get', headers, sys._getframe().f_code.co_name)
    req = requests.get(stream_url, headers=headers, cookies=auth.load_cookies(), verify=config.VERIFY_SSL)
    playlist = req.text
    playlist_file = os.path.join(config.CONFIG.dir, 'playlist-{}.m3u8'.format(time.strftime("%Y-%m-%d")))
    LOG.debug('writing playlist to: {}'.format(playlist_file))
    with open(playlist_file, 'w') as f:
        f.write(playlist)
    LOG.debug('save_playlist_to_file: {}'.format(playlist))


def play_stream(game_data, team_to_play, feedtype, date_str, fetch, login_func, get_session_key_func):
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
        auth_cookie = auth.get_auth_cookie()
        if auth_cookie is None:
            login_func()
            # auth.login(config.CONFIG.parser['username'],
            #            config.CONFIG.parser['password'],
            #            config.CONFIG.parser.getboolean('use_rogers', False))
        LOG.debug('Authorization cookie: {}'.format(auth.get_auth_cookie()))

        media_playback_id, event_id = select_feed_for_team(game_rec, team_to_play, feedtype)
        if media_playback_id is not None:
            stream_url, media_auth = fetch_stream(game_rec['game_pk'], media_playback_id, event_id, get_session_key_func)
            if stream_url is not None:
                if config.DEBUG:
                    save_playlist_to_file(stream_url, media_auth)
                streamlink(stream_url, media_auth,
                           get_fetch_filename(date_str, game_rec, feedtype, fetch))
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


def streamlink(stream_url, media_auth, fetch_filename=None):
    LOG.debug("Stream url: " + stream_url)
    auth_cookie_str = "Authorization=" + auth.get_auth_cookie()
    media_auth_cookie_str = media_auth
    user_agent_hdr = 'User-Agent=' + config.CONFIG.ua_iphone

    video_player = config.CONFIG.parser['video_player']
    streamlink_cmd = ["streamlink",
                      "--http-no-ssl-verify",
                      "--player-no-close",
                      "--http-cookie", auth_cookie_str,
                      "--http-cookie", media_auth_cookie_str,
                      "--http-header", user_agent_hdr]
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
