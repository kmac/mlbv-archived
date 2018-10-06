"""
Streaming functions
"""

import logging

from datetime import datetime
from datetime import timezone
from dateutil import parser

import mlbam.common.config as config
import mlbam.common.stream as stream
import mlbam.common.util as util


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
            if game_rec['feed']:
                feedtype = list(game_rec['feed'].keys())[0]
                LOG.info("Chose '%s' feed (override with --feed option)", feedtype)
        if feedtype not in game_rec['feed']:
            LOG.error("Feed is not available: %s", feedtype)
            return None, None
        return game_rec['feed'][feedtype]['mediaPlaybackId'], game_rec['feed'][feedtype]['mediaState']
    return None, None


def find_highlight_url_for_team(game_rec, feedtype):
    if feedtype not in config.HIGHLIGHT_FEEDTYPES:
        raise Exception('highlight: feedtype must be condensed or recap')
    if feedtype in game_rec['feed'] and 'playback_url' in game_rec['feed'][feedtype]:
        return game_rec['feed'][feedtype]['playback_url']
    LOG.error('No playback_url found for %s vs %s', game_rec['away']['abbrev'], game_rec['home']['abbrev'])
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


def play_stream(game_rec, team_to_play, feedtype, date_str, fetch, from_start, inning_ident, is_multi_highlight=False):
    if game_rec['doubleHeader'] != 'N':
        LOG.info('Selected game number %s of doubleheader', game_rec['gameNumber'])
    if feedtype is not None and feedtype in config.HIGHLIGHT_FEEDTYPES:
        # handle condensed/recap
        playback_url = find_highlight_url_for_team(game_rec, feedtype)
        if playback_url is None:
            util.die("No playback url for feed '{}'".format(feedtype))
        stream.play_highlight(playback_url,
                              stream.get_fetch_filename(date_str, game_rec['home']['abbrev'],
                                                        game_rec['away']['abbrev'], feedtype, fetch),
                              is_multi_highlight)
    else:
        # handle full game (live or archive)
        # this is the only feature requiring an authenticated session
        import mlbam.mlbsession as mlbsession
        mlb_session = mlbsession.MLBSession()

        media_playback_id, media_state = select_feed_for_team(game_rec, team_to_play, feedtype)
        if media_playback_id is not None:
            stream_url = mlb_session.lookup_stream_url(game_rec['game_pk'], media_playback_id)
            if stream_url is not None:
                offset = None
                if config.SAVE_PLAYLIST_FILE:
                    mlb_session.save_playlist_to_file(stream_url)
                if inning_ident:
                    offset = _calculate_inning_offset(inning_ident, media_state, game_rec)
                stream.streamlink(stream_url, mlb_session,
                                  stream.get_fetch_filename(date_str, game_rec['home']['abbrev'],
                                                            game_rec['away']['abbrev'], feedtype, fetch),
                                  from_start, offset)
            else:
                LOG.error("No stream URL found")
        else:
            LOG.info("No game stream found for %s", team_to_play)
    return 0


def _lookup_inning_timestamp_via_playbyplay(game_pk, inning, inning_half='top', overwrite_json=True):
    LOG.info("Retrieving inning info to locate '%s %s' inning", inning_half, inning)
    # url = 'http://statsapi.mlb.com/api/v1/game/{gamepk}/playByPlay'.format(gamepk=game_pk)
    url = 'http://statsapi.mlb.com/api/v1/game/{gamepk}/playByPlay?fields=allPlays,about,startTime,inning,halfInning'.format(gamepk=game_pk)
    json_data = util.request_json(url, 'playbyplay')

    # json_data = util.request_json(live_url, 'live')
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
    # playbyplay_url = 'http://statsapi.mlb.com/api/v1/game/{gamepk}/playByPlay?fields=allPlays,about,startTime,inning,halfInning'.format(gamepk=game_pk)
    url = 'https://statsapi.mlb.com/api/v1/game/{gamepk}/feed/live'.format(gamepk=game_pk)
    json_data  = util.request_json(url, 'live')

    # json_data = util.request_json(live_url, 'live')
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
    # inning_start_datetime = parser.parse(inning_timestamp_str)
    # inning_start_datetime = datetime.strptime(inning_timestamp_str, '%Y%m%d_%H%M%S').replace(tzinfo=timezone.utc)
    # inning_start_timestamp = inning_start_datetime.timestamp()

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
        # Issue #9: apply the offset if provided (assume provided if not default value):
        stream_start_offset_secs = config.CONFIG.parser.getint('stream_start_offset_secs',
                                                               config.DEFAULT_STREAM_START_OFFSET_SECS)
        if stream_start_offset_secs != config.DEFAULT_STREAM_START_OFFSET_SECS:
            LOG.info("Applying non-default stream start offset: %s seconds", stream_start_offset_secs)
            offset_secs -= stream_start_offset_secs
        LOG.debug("now_timestamp: %s, inning_start_timestamp: %s, offset=%s", now_timestamp, inning_start_timestamp, offset_secs)
        logstr = "Calculated live game negative inning offset (from now): %s"
    else:
        #     start      inning        endofstream
        #     | <--------> |                |
        #         offset
        LOG.info("Archive game: game start: %s, inning start: %s", first_play_timestamp_str, inning_timestamp_str)
        # first_play_timestamp = parser.parse(first_play_timestamp_str).timestamp()
        game_start_timestamp = game_rec['mlbdate'].timestamp()
        # first_play_timestamp = datetime.strptime(first_play_timestamp_str, '%Y%m%d_%H%M%S').replace(tzinfo=timezone.utc).timestamp()
        offset_secs = inning_start_timestamp - game_start_timestamp
        offset_secs += config.CONFIG.parser.getint('stream_start_offset_secs', 240)
        LOG.debug("inning_start_timestamp: %s, first_play_timestamp: %s, offset=%s",
                  inning_start_timestamp, first_play_timestamp, offset_secs)
        logstr = "Calculated archive game inning offset (from start): %s"

    hours, remainder_secs = divmod(offset_secs, 3600)
    minutes, secs = divmod(remainder_secs, 60)
    offset = '{:02d}:{:02d}:{:02d}'.format(int(hours), int(minutes), int(secs))
    LOG.info(logstr, offset)
    return offset
