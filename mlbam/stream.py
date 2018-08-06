"""
Streaming functions
"""

import logging
import os
import subprocess

from datetime import datetime
from datetime import timezone
from dateutil import parser

import mlbam.config as config
import mlbam.util as util


LOG = logging.getLogger(__name__)


def _has_game_started(start_time_utc):
    return start_time_utc.replace(timezone.utc) < datetime.now(timezone.utc)


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
                LOG.info("Chose '%s' feed (override with --feed option)", feedtype)
        if feedtype not in game_rec['feed']:
            LOG.error("Feed is not available: {}".format(feedtype))
            return None, None
        return game_rec['feed'][feedtype]['mediaPlaybackId'], game_rec['feed'][feedtype]['mediaState']
    return None, None


def find_highlight_url_for_team(game_rec, feedtype):
    if feedtype not in config.HIGHLIGHT_FEEDTYPES:
        raise Exception('highlight: feedtype must be condensed or recap')
    if feedtype in game_rec['feed'] and 'playback_url' in game_rec['feed'][feedtype]:
        return game_rec['feed'][feedtype]['playback_url']
    LOG.error('No playback_url found for {} vs {}'.format(game_rec['away']['abbrev'], game_rec['home']['abbrev']))
    return None


def get_game_rec(game_data, team_to_play, game_number_str):
    """ game_number_str: is an string 1 or 2 indicating game number for doubleheader
    """
    game_rec = None
    for game_pk in game_data:
        if team_to_play in (game_data[game_pk]['away']['abbrev'], game_data[game_pk]['home']['abbrev']):
            if game_data[game_pk]['doubleHeader'] != 'N' and game_number_str != game_data[game_pk]['gameNumber']:
                # game is doubleheader but not our game_number
                continue
            game_rec = game_data[game_pk]
            break
    if game_rec is None:
        if int(game_number_str) > 1:
            util.die("No second game available for team {}".format(team_to_play))
        util.die("No game found for team {}".format(team_to_play))
    return game_rec


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


def play_stream(game_rec, team_to_play, feedtype, date_str, fetch, from_start, inning_ident, is_multi_highlight=False):
    if game_rec['doubleHeader'] != 'N':
        LOG.info('Selected game number %s of doubleheader', game_rec['gameNumber'])
    if feedtype is not None and feedtype in config.HIGHLIGHT_FEEDTYPES:
        # handle condensed/recap
        playback_url = find_highlight_url_for_team(game_rec, feedtype)
        if playback_url is None:
            util.die("No playback url for feed '{}'".format(feedtype))
        play_highlight(playback_url, get_fetch_filename(date_str, game_rec, feedtype, fetch), is_multi_highlight)
    else:
        # handle full game (live or archive)
        # this is the only feature requiring an authenticated session
        import mlbam.session as session
        mlb_session = session.MLBSession()

        media_playback_id, media_state = select_feed_for_team(game_rec, team_to_play, feedtype)
        if media_playback_id is not None:
            stream_url = mlb_session.lookup_stream_url(game_rec['game_pk'], media_playback_id)
            if stream_url is not None:
                offset = None
                if config.SAVE_PLAYLIST_FILE:
                    mlb_session.save_playlist_to_file(stream_url)
                if inning_ident:
                    offset = _calculate_inning_offset(inning_ident, media_state, game_rec)
                streamlink(stream_url, mlb_session, get_fetch_filename(date_str, game_rec, feedtype, fetch), from_start, offset)
            else:
                LOG.error("No stream URL found")
        else:
            LOG.info("No game stream found for %s", team_to_play)
    return 0


def get_fetch_filename(date_str, game_rec, feedtype, fetch):
    if fetch:
        suffix = 'ts'
        if feedtype is None:
            fetch_filename = '{}-{}-{}.{}'.format(date_str, game_rec['away']['abbrev'], game_rec['home']['abbrev'], suffix)
        else:
            if feedtype in ('recap', 'condensed', ):
                suffix = 'mp4'
            fetch_filename = '{}-{}-{}-{}.{}'.format(date_str, game_rec['away']['abbrev'], game_rec['home']['abbrev'], feedtype, suffix)
        return _uniquify_fetch_filename(fetch_filename, strategy='index')
    return None


def _lookup_inning_timestamp_via_playbyplay(game_pk, inning, inning_half='top', overwrite_json=True):
    LOG.info("Retrieving inning info to locate '{} {}' inning".format(inning_half, inning))
    # url = 'http://statsapi.mlb.com/api/v1/game/{gamepk}/playByPlay'.format(gamepk=game_pk)
    url = 'http://statsapi.mlb.com/api/v1/game/{gamepk}/playByPlay?fields=allPlays,about,startTime,inning,halfInning'.format(gamepk=game_pk)
    json_data  = util.request_json(url, 'playbyplay')

    #json_data = util.request_json(live_url, 'live')
    if 'allPlays' in json_data:
        if json_data['allPlays'] is None or len(json_data['allPlays']) < 1:
            LOG.debug("_lookup_inning_timestamp: no play data for %s", url)
            return None, None, None, None
    else:
        LOG.debug("_lookup_inning_timestamp: no live data for %s", url)
        return None, None, None, None

    first_play = None
    for play in json_data['allPlays']:
        if first_play is None:
            first_play_timestamp_str = str(play['about']['startTime'])
            first_play_timestamp = parser.parse(first_play_timestamp_str).timestamp()
            LOG.debug("First play: %s", first_play_timestamp_str)
            LOG.debug("First play data: %s", play)
        if str(play['about']['inning']) == inning and str(play['about']['halfInning']) == inning_half:
            inning_start_timestamp_str = str(play['about']['startTime'])
            inning_start_timestamp = parser.parse(inning_start_timestamp_str).timestamp()
            LOG.info("Found inning start: %s", inning_start_timestamp_str)
            LOG.debug("Inning start play data: %s", play)
            return first_play_timestamp, first_play_timestamp_str, inning_start_timestamp, inning_start_timestamp_str
    LOG.warn("Could not locate '{} {}' inning".format(inning_half, inning))
    return first_play, first_play_timestamp_str, None, None


def _lookup_inning_timestamp_via_live(game_pk, inning, inning_half='top', overwrite_json=True):
    LOG.info("Retrieving inning info to locate '{} {}' inning".format(inning_half, inning))
    # playbyplay_url = 'http://statsapi.mlb.com/api/v1/game/{gamepk}/playByPlay'.format(gamepk=game_pk)
    #playbyplay_url = 'http://statsapi.mlb.com/api/v1/game/{gamepk}/playByPlay?fields=allPlays,about,startTime,inning,halfInning'.format(gamepk=game_pk)
    url = 'https://statsapi.mlb.com/api/v1/game/{gamepk}/feed/live'.format(gamepk=game_pk)
    json_data  = util.request_json(url, 'live')

    #json_data = util.request_json(live_url, 'live')
    if 'liveData' in json_data and 'plays' in json_data['liveData'] and 'allPlays' in json_data['liveData']['plays']:
        if json_data['liveData']['plays']['allPlays'] is None or len(json_data['liveData']['plays']['allPlays']) < 1:
            LOG.debug("_lookup_inning_timestamp: no play data for %s", url)
            return None, None, None, None
    else:
        LOG.debug("_lookup_inning_timestamp: no live data for %s", url)
        return None, None, None, None

    first_play = None
    for play in json_data['liveData']['plays']['allPlays']:
        if first_play is None:
            first_play_timestamp_str = str(play['about']['startTts'])
            first_play_timestamp = datetime.strptime(first_play_timestamp_str, '%Y%m%d_%H%M%S').replace(tzinfo=timezone.utc).timestamp()
            LOG.debug("First play: %s", first_play_timestamp_str)
            LOG.debug("First play data: %s", play)
        if str(play['about']['inning']) == inning and str(play['about']['halfInning']) == inning_half:
            inning_start_timestamp_str = str(play['about']['startTts'])
            inning_start_timestamp  = datetime.strptime(inning_start_timestamp_str, '%Y%m%d_%H%M%S').replace(tzinfo=timezone.utc).timestamp()
            LOG.info("Found inning start: %s", inning_start_timestamp_str)
            LOG.debug("Inning start play data: %s", play)
            return first_play_timestamp, first_play_timestamp_str, inning_start_timestamp, inning_start_timestamp_str
    LOG.warn("Could not locate '{} {}' inning".format(inning_half, inning))
    return first_play, first_play_timestamp_str, None, None


def _calculate_inning_offset(inning_offset, media_state, game_rec):
    inning_half = 'top'
    if inning_offset.startswith('b'):
        inning_half = 'bottom'
    if len(inning_offset) > 1 and inning_offset[-2].isnumeric():
        inning = inning_offset[-2:]  # double digits, extra innings
    else:
        inning = inning_offset[-1]  # single digit inning
    first_play_timestamp, first_play_timestamp_str, inning_start_timestamp, inning_timestamp_str = \
        _lookup_inning_timestamp_via_playbyplay(game_rec['game_pk'], inning, inning_half)
    if inning_start_timestamp is None:
        LOG.error(("Inning '%s' not found in play-by-play data. "
                   "Proceeding without inning input", inning_offset))
        return None

    # inning_timestamp_str is of form: 2018-04-02T17:08:23.000Z
    #inning_start_datetime = parser.parse(inning_timestamp_str)
    #inning_start_datetime = datetime.strptime(inning_timestamp_str, '%Y%m%d_%H%M%S').replace(tzinfo=timezone.utc)
    #inning_start_timestamp = inning_start_datetime.timestamp()

    # now calculate the HH:MM:SS offset for livestream.
    # It is complicated by:
    #     - if stream is live then the offset is from the end of stream
    #     - if stream is archive then offset is from beginning of stream
    if media_state == 'MEDIA_ON':
        #     start          offset       endofstream
        #     |        | <----------------> |
        #            inning
        LOG.info("Live game: game start: %s, inning start: %s", game_rec['mlbdate'], inning_timestamp_str)
        now_timestamp = datetime.now(timezone.utc).timestamp()
        offset_secs = now_timestamp - inning_start_timestamp
        LOG.debug("now_timestamp: %s, inning_start_timestamp: %s, offset=%s", now_timestamp, inning_start_timestamp, offset_secs)
        logstr = "Calculated live game negative inning offset (from now): %s"
    else:
        #     start      inning        endofstream
        #     | <--------> |                |
        #         offset
        LOG.info("Archive game: game start: %s, inning start: %s", first_play_timestamp_str, inning_timestamp_str)
        #first_play_timestamp = parser.parse(first_play_timestamp_str).timestamp()
        game_start_timestamp = game_rec['mlbdate'].timestamp()
        #first_play_timestamp = datetime.strptime(first_play_timestamp_str, '%Y%m%d_%H%M%S').replace(tzinfo=timezone.utc).timestamp()
        offset_secs = inning_start_timestamp - game_start_timestamp
        offset_secs += config.CONFIG.parser.getint('stream_start_offset', 240)
        LOG.debug("inning_start_timestamp: %s, first_play_timestamp: %s, offset=%s",
                  inning_start_timestamp, first_play_timestamp, offset_secs)
        logstr = "Calculated archive game inning offset (from start): %s"

    hours, remainder_secs = divmod(offset_secs, 3600)
    minutes, secs = divmod(remainder_secs, 60)
    offset = '{:02d}:{:02d}:{:02d}'.format(int(hours), int(minutes), int(secs))
    LOG.info(logstr, offset)
    return offset


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
    # the --playe-no-close is required so it doesn't shut things down 
    # prematurely after the stream is fully fetched
    streamlink_cmd = ["streamlink", "--player-no-close", ]
    if fetch_filename is not None:
        streamlink_cmd.append("--output")
        streamlink_cmd.append(fetch_filename)
    elif video_player is not None and video_player != '':
        LOG.debug('Using video_player: {}'.format(video_player))
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

    LOG.info('Playing highlight via streamlink: ' + str(streamlink_cmd))
    subprocess.run(streamlink_cmd)


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


def streamlink(stream_url, mlb_session, fetch_filename=None, from_start=False, offset=None):
    LOG.debug("Stream url: " + stream_url)
    # media_auth_cookie_str = access_token
    # user_agent_hdr = 'User-Agent=' + config.CONFIG.ua_iphone
    user_agent_hdr = 'User-Agent=' + config.CONFIG.ua_pc

    video_player = config.CONFIG.parser['video_player']
    streamlink_cmd = ["streamlink",
                      "--http-no-ssl-verify",
                      "--player-no-close",
                      "--http-header", user_agent_hdr,
                      "--http-cookie", "Authorization=" + mlb_session.access_token]

    # include our cookies
    # cookie_dict = mlb_session.get_cookie_dict()
    # for cookie_name in cookie_dict:
    #     streamlink_cmd.append("--http-cookie")
    #     streamlink_cmd.append('{}={}'.format(cookie_name, cookie_dict[cookie_name]))

    if from_start:
        streamlink_cmd.append("--hls-live-restart")
        LOG.info("Starting from beginning [--hls-live-restart]")
    elif offset:
        streamlink_cmd.append("--hls-start-offset")
        streamlink_cmd.append(offset)
        LOG.debug("Using --hls-start-offset %s", offset)

    if fetch_filename is not None:
        fetch_filename = _uniquify_fetch_filename(fetch_filename)
        streamlink_cmd.append("--output")
        streamlink_cmd.append(fetch_filename)
    elif video_player is not None and video_player != '':
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
