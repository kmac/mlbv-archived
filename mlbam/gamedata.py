"""
Models the game data retrieved via JSON.
"""
import json
import logging
import os
import pprint
import requests
import sys
import time

from datetime import datetime
from datetime import timedelta

import mlbam.auth as auth
import mlbam.config as config
import mlbam.util as util


LOG = logging.getLogger(__name__)


TEAM_CODES = ('ari', 'atl', 'bal', 'bos', 'chc', 'cws', 'cin', 'cle', 'col', 'det', 'fla', 'hou', 'kan', 'laa', 'lad',
              'mil', 'min', 'nym', 'nyy', 'oak', 'phi', 'pit', 'sd', 'sf', 'sea', 'stl', 'tb', 'tex', 'tor', 'was')


# this map is used to transform the statsweb feed name to something shorter
FEEDTYPE_MAP = {
    'away': 'a',
    'home': 'h',
    'french': 'fr',
    'national': 'nat',
    'condensed': 'cnd',
    'recap': 'rcp',
    'audio-away': 'aud-a',
    'audio-home': 'aud-h',
}

FEEDTYPE_MAP = {
    'away': 'a',
    'home': 'h',
    'french': 'fr',
    'national': 'nat',
    'condensed': 'cnd',
    'recap': 'rcp',
    'audio-away': 'aud-a',
    'audio-home': 'aud-h',
}


def get_feedtype_keystring():
    reverse_list = list()
    for longkey in FEEDTYPE_MAP:
        reverse_list.append('{}:{}'.format(FEEDTYPE_MAP[longkey], longkey))
    return ', '.join(reverse_list)


def is_fav(game_rec):
    if 'favourite' in game_rec:
        return game_rec['favourite']
    if config.CONFIG.parser['favs'] is None or config.CONFIG.parser['favs'] == '':
        return False
    for fav in config.CONFIG.parser['favs'].split(','):
        fav = fav.strip()
        if fav in (game_rec['away']['abbrev'], game_rec['home']['abbrev']):
            return True
    return False


def filter_favs(game_rec):
    """Returns the game_rec if the game matches the favourites, or if no filtering is active."""
    if not config.CONFIG.parser.getboolean('filter', 'false'):
        return game_rec
    if config.CONFIG.parser['favs'] is None or config.CONFIG.parser['favs'] == '':
        return game_rec
    for fav in config.CONFIG.parser['favs'].split(','):
        fav = fav.strip()
        if fav in (game_rec['away']['abbrev'], game_rec['home']['abbrev']):
            return game_rec
    return None


class GameData:

    def __init__(self, feedtype_map=FEEDTYPE_MAP):
        self.game_data_list = list()
        self.feedtype_map = feedtype_map

    def convert_feedtype_to_short(self, feedtype):
        if feedtype in self.feedtype_map:
            return self.feedtype_map[feedtype]
        return feedtype

    def convert_to_long_feedtype(self, feed):
        if feed in self.feedtype_map:
            return feed
        for feedtype in self.feedtype_map:
            if self.feedtype_map[feedtype] == feed:
                return feedtype
        return feed

    def __get_feeds_for_display(self, game_rec):
        non_highlight_feeds = list()
        use_short_feeds = config.CONFIG.parser.getboolean('use_short_feeds', True)
        for feed in sorted(game_rec['feed'].keys()):
            if feed not in config.HIGHLIGHT_FEEDTYPES and not feed.startswith('audio-'):
                if use_short_feeds:
                    non_highlight_feeds.append(self.convert_feedtype_to_short(feed))
                else:
                    non_highlight_feeds.append(feed)
        highlight_feeds = list()
        for feed in game_rec['feed'].keys():
            if feed in config.HIGHLIGHT_FEEDTYPES and not feed.startswith('audio-'):
                if use_short_feeds:
                    highlight_feeds.append(self.convert_feedtype_to_short(feed))
                else:
                    highlight_feeds.append(feed)
        return '{:7} {}'.format('/'.join(non_highlight_feeds), '/'.join(highlight_feeds))

    @staticmethod
    def _fetch_json_from_url(url, suffix, overwrite_json=True):
        if config.SAVE_JSON_FILE_BY_TIMESTAMP:
            json_file = os.path.join(config.CONFIG.dir, 'mlbgamedata-{}-{}.json'.format(suffix, time.strftime("%Y-%m-%d-%H%M")))
        else:
            json_file = os.path.join(config.CONFIG.dir, 'mlbgamedata-{}.json'.format(suffix))
        if overwrite_json or not os.path.exists(json_file):
            LOG.debug('Getting url={} ...'.format(url))
            # query nhl.com for today's schedule
            headers = {
                'User-Agent': config.CONFIG.ua_iphone,
                'Connection': 'close'
            }
            util.log_http(url, 'get', headers, sys._getframe().f_code.co_name)
            r = requests.get(url, headers=headers, cookies=auth.load_cookies(), verify=config.VERIFY_SSL)

            with open(json_file, 'w') as f:  # write date to json_file
                f.write(r.text)

        with open(json_file) as games_file:
            json_data = json.load(games_file)

        return json_data

    def _get_game_data(self, date_str=None, overwrite_json=True):
        if date_str is None:
            date_str = time.strftime("%Y-%m-%d")

        # https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2018-03-26&endDate=2018-03-26&hydrate=schedule.teams,schedule.linescore,schedule.game.content.media.epg
        url = ('{0}/api/v1/schedule?sportId=1&startDate={1}&endDate={1}&hydrate='
               'schedule.teams,schedule.linescore,schedule.game.content.media.epg').format(config.CONFIG.api_url, date_str)

        json_data = self._fetch_json_from_url(url, 'top', overwrite_json)

        game_data = dict()  # we return this dictionary

        if json_data['dates'] is None or len(json_data['dates']) < 1:
            LOG.debug("_get_game_data: no game data for {}".format(date_str))
            return None

        for game in json_data['dates'][0]['games']:
            # LOG.debug('game: {}'.format(game))
            game_pk_str = str(game['gamePk'])
            game_data[game_pk_str] = dict()
            game_rec = game_data[game_pk_str]
            game_rec['game_pk'] = game_pk_str

            game_rec['abstractGameState'] = str(game['status']['abstractGameState'])  # Preview, Live, Final
            game_rec['codedGameState'] = str(game['status']['codedGameState'])  # is something like: F, O, C, I
            game_rec['detailedState'] = str(game['status']['detailedState'])  # is something like: Scheduled, Live, Final, In Progress, Critical
            game_rec['doubleHeader'] = str(game['doubleHeader'])
            game_rec['mlbdate'] = datetime.strptime(str(game['gameDate']), "%Y-%m-%dT%H:%M:%SZ")
            game_rec['gamesInSeries'] = str(game['gamesInSeries'])
            game_rec['seriesGameNumber'] = str(game['seriesGameNumber'])

            # Live game data for a given game
            game_rec['link'] = str(game['link'])  # this is the link to the live game data
            live_url = '{}{}'.format(config.CONFIG.api_url, game_rec['link'])
            live_data = self._fetch_json_from_url(live_url, 'live', overwrite_json)

            game_rec['linescore'] = dict()
            if 'currentInning' in live_data['liveData']['linescore']:
                game_rec['linescore']['currentInning'] = str(live_data['liveData']['linescore']['currentInning'])
            else:
                game_rec['linescore']['currentInningOrdinal'] = '0'
            if 'currentInningOrdinal' in live_data['liveData']['linescore']:
                game_rec['linescore']['currentInningOrdinal'] = str(live_data['liveData']['linescore']['currentInningOrdinal'])
                game_rec['linescore']['inningState'] = str(live_data['liveData']['linescore']['inningState'])[:3]
            else:
                game_rec['linescore']['currentInningOrdinal'] = 'Not Started'
                game_rec['linescore']['inningState'] = ''

            game_rec['flags'] = dict()
            for attr in ('perfectGame', 'noHitter'):
                if attr in live_data['gameData']['flags']:
                    game_rec['flags'][attr] = str(live_data['gameData']['flags'][attr])

            for teamtype in ('home', 'away'):
                # pprint.pprint(live_data['gameData']['teams'])
                game_rec[teamtype] = dict()
                # seems to be two different formats for away/home team info(!)
                if 'name' in live_data['gameData']['teams'][teamtype] and 'abbrev' in live_data['gameData']['teams'][teamtype]['name']:
                    game_rec[teamtype] = {
                        'abbrev':   str(live_data['gameData']['teams'][teamtype]['name']['abbrev']).lower(),
                        'display':  str(live_data['gameData']['teams'][teamtype]['name']['display']),
                        'brief':    str(live_data['gameData']['teams'][teamtype]['name']['brief']),
                        'full':     str(live_data['gameData']['teams'][teamtype]['name']['full']),
                        'league':   str(live_data['gameData']['teams'][teamtype]['league']),
                        'division': str(live_data['gameData']['teams'][teamtype]['division']),
                    }
                elif 'abbreviation' in live_data['gameData']['teams'][teamtype]:
                    game_rec[teamtype] = {
                        'abbrev':   str(live_data['gameData']['teams'][teamtype]['abbreviation']).lower(),
                        'display':  str(live_data['gameData']['teams'][teamtype]['shortName']),
                        'brief':    str(live_data['gameData']['teams'][teamtype]['teamName']),
                        'full':     str(live_data['gameData']['teams'][teamtype]['name']),
                        'league':   'n/a',
                        'division': 'n/a',
                    }
                else:
                    LOG.error("Unexpected live data['gameData']['teams'] for teamtype=%s", teamtype)
                    pprint.pprint(live_data['gameData']['teams'][teamtype])
                    game_rec[teamtype] = {
                        'abbrev': 'n/a', 'display': 'n/a', 'brief': 'n/a', 'full': 'n/a', 'league': 'n/a', 'division': 'n/a',
                    }

                if teamtype in live_data['liveData']['linescore']:
                    game_rec['linescore'][teamtype] = {
                        'runs':  str(live_data['liveData']['linescore'][teamtype]['runs']),
                        'hits':  str(live_data['liveData']['linescore'][teamtype]['hits']),
                        'errors': str(live_data['liveData']['linescore'][teamtype]['errors']),
                    }
                else:
                    game_rec['linescore'][teamtype] = {'runs':  '0', 'hits':  '0', 'errors': '0'}

            game_rec['favourite'] = is_fav(game_rec)

            game_rec['feed'] = dict()
            if game_rec['abstractGameState'] == 'Preview':
                continue

            # This gives the media content for a given game
            # ignore the link for now, focus on getting the content_link going
            game_rec['content_link'] = str(game['content']['link'])  # this is the link to the content
            content_url = '{}{}'.format(config.CONFIG.api_url, game_rec['content_link'])
            content_json = self._fetch_json_from_url(content_url, 'content', overwrite_json)

            # epg
            if 'media' in content_json and 'epg' in content_json['media']:
                for media in content_json['media']['epg']:
                    if media['title'] == 'MLBTV':
                        for stream in media['items']:
                            if stream['mediaFeedType'] != 'COMPOSITE' and stream['mediaFeedType'] != 'ISO':
                                feedtype = str(stream['mediaFeedType']).lower()  # home, away, national, french, ...
                                game_rec['feed'][feedtype] = dict()
                                game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaId'])
                                game_rec['feed'][feedtype]['eventId'] = str(stream['id'])
                                game_rec['feed'][feedtype]['callLetters'] = str(stream['callLetters'])
                    elif media['title'] == 'Extended Highlights':
                        feedtype = 'condensed'
                        if len(media['items']) > 0:
                            game_rec['feed'][feedtype] = dict()
                            stream = media['items'][0]
                            game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaId'])
                            for playback_item in stream['playbacks']:
                                if playback_item['name'] == config.CONFIG.playback_scenario:
                                    game_rec['feed'][feedtype]['playback_url'] = playback_item['url']
                    elif media['title'] == 'Recap':
                        feedtype = 'recap'
                        if len(media['items']) > 0:
                            game_rec['feed'][feedtype] = dict()
                            stream = media['items'][0]
                            game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaId'])
                            for playback_item in stream['playbacks']:
                                if playback_item['name'] == config.CONFIG.playback_scenario:
                                    game_rec['feed'][feedtype]['playback_url'] = playback_item['url']
                    # elif media['title'] == 'Audio':
                    #     for stream in media['items']:
                    #         feedtype = 'audio-' + str(stream['mediaFeedType']).lower()  # home, away, national, french, ...
                    #         game_rec['feed'][feedtype] = dict()
                    #         game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaId'])
                    #         game_rec['feed'][feedtype]['eventId'] = str(stream['id'])
                    #         game_rec['feed'][feedtype]['callLetters'] = str(stream['callLetters'])
        return game_data

    def fetch_game_data(self, game_date, num_days=1, show_games=True):
        """ https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2018-03-26&endDate=2018-03-26&
                 hydrate=schedule.teams,schedule.linescore,schedule.game.content.media.epg
        """
        game_data_list = list()
        show_scores = config.CONFIG.parser.getboolean('scores')
        for i in range(0, num_days):
            game_data = self._get_game_data(game_date)
            outl = list()  # holds list of strings for output
            print_outl = False
            if game_data is not None:
                game_data_list.append(game_data)
                if not show_games:
                    continue
                live_game_pks = list()
                for game_pk in game_data:
                    if game_data[game_pk]['abstractGameState'] == 'Live':
                        if filter_favs(game_data[game_pk]) is not None:
                            live_game_pks.append(game_pk)

                # print header
                date_hdr = '{:7}{}'.format('', '{}'.format(game_date))
                if show_scores:
                    outl.append("{:64} | {:^5} | {:^9} | {}".format(date_hdr, 'Score', 'State', 'Feeds'))
                    outl.append("{}|{}|{}|{}".format('-' * 65, '-' * 7, '-' * 11, '-' * 14))
                else:
                    outl.append("{:64} | {:^9} | {}".format(date_hdr, 'State', 'Feeds'))
                    outl.append("{}|{}|{}".format('-' * 65, '-' * 11, '-' * 12))

                if len(live_game_pks) > 0:
                    if show_scores:
                        outl.append("{:64} |{}|{}|{}".format('Live Games:', ' ' * 7, ' ' * 11, ' ' * 12))
                    else:
                        outl.append("{:64} |{}|{}".format('Live Games:', ' ' * 11, ' ' * 12))
                    for game_pk in live_game_pks:
                        if filter_favs(game_data[game_pk]) is not None:
                            outl.extend(self.show_game_details(game_pk, game_data[game_pk]))
                            print_outl = True
                    if show_scores:
                        outl.append("{:64} |{}|{}|{}".format('-----', ' ' * 7, ' ' * 11, ' ' * 12))
                    else:
                        outl.append("{:64} |{}|{}".format('-----', ' ' * 11, ' ' * 12))
                for game_pk in game_data:
                    if game_data[game_pk]['abstractGameState'] != 'Live':
                        if filter_favs(game_data[game_pk]) is not None:
                            outl.extend(self.show_game_details(game_pk, game_data[game_pk]))
                            print_outl = True
                # print(' ' * 5, get_feedtype_keystring())
            else:
                outl.append("No game data for {}".format(game_date))
                print_outl = True
            if print_outl:
                print('\n'.join(outl))
                if num_days > 1:
                    print('')  # add line feed between days

            game_date = datetime.strftime(datetime.strptime(game_date, "%Y-%m-%d") + timedelta(days=1), "%Y-%m-%d")

        return game_data_list

    def show_game_details(self, game_pk, game_rec):
        outl = list()
        color_on = ''
        color_off = ''
        if is_fav(game_rec):
            if config.CONFIG.parser['fav_colour'] != '':
                color_on = util.fg_ansi_colour(config.CONFIG.parser['fav_colour'])
                color_off = util.ANSI_CONTROL_CODES['reset']
        show_scores = config.CONFIG.parser.getboolean('scores')
        game_info_str = "{}: {} ({}) at {} ({})".format(util.convert_time_to_local(game_rec['mlbdate']),
                                                        game_rec['away']['display'], game_rec['away']['abbrev'].upper(),
                                                        game_rec['home']['display'], game_rec['home']['abbrev'].upper())
        game_state = ''
        game_state_color_on = color_on
        game_state_color_off = color_off
        LOG.debug("Checking game state: %s, %s", game_rec['abstractGameState'], game_rec['detailedState'])
        if game_rec['abstractGameState'] not in ('Preview', ):
            if show_scores:
                if 'Critical' in game_rec['detailedState']:
                    game_state_color_on = util.fg_ansi_colour(config.CONFIG.parser['game_critical_colour'])
                    game_state_color_off = util.ANSI_CONTROL_CODES['reset']
                if game_rec['detailedState'] in ('Final', ):
                    game_state = game_rec['detailedState']
                    if int(game_rec['linescore']['currentInning']) != 9:
                        game_state += '({})'.format(game_rec['linescore']['currentInning'])
                else:
                    game_state = '{} {}'.format(game_rec['linescore']['inningState'].title(),
                                                game_rec['linescore']['currentInningOrdinal'])
            else:
                game_state = game_rec['abstractGameState']
                if 'In Progress - ' in game_rec['detailedState']:
                    game_state = game_rec['detailedState'].split('In Progress - ')[-1]
                elif game_rec['detailedState'] not in ('Live', 'Final', 'Scheduled', 'In Progress'):
                    game_state = game_rec['detailedState']
        # else:
        #    game_state = 'Pending'
        if show_scores:
            score = ''
            if game_rec['abstractGameState'] not in ('Preview', ):
                score = '{}-{}'.format(game_rec['linescore']['away']['runs'], game_rec['linescore']['home']['runs'])
            outl.append("{0}{2:<64}{1} | {0}{3:^5}{1} | {4}{5:>9}{6} | {0}{7}{1}".format(color_on, color_off,
                                                                                         game_info_str, score,
                                                                                         game_state_color_on,
                                                                                         game_state,
                                                                                         game_state_color_off,
                                                                                         self.__get_feeds_for_display(game_rec)))
        else:
            outl.append("{0}{2:<64}{1} | {0}{3:^9}{1} | {0}{4}{1}".format(color_on, color_off,
                                                                          game_info_str, game_state,
                                                                          self.__get_feeds_for_display(game_rec)))
        if config.CONFIG.parser.getboolean('debug') and config.CONFIG.parser.getboolean('verbose'):
            for feedtype in game_rec['feed']:
                outl.append('    {}: {}  [game_pk:{}, mediaPlaybackId:{}]'.format(feedtype,
                                                                                  game_rec['abstractGameState'],
                                                                                  game_pk,
                                                                                  game_rec['feed'][feedtype]['mediaPlaybackId']))
        return outl

    def get_audio_stream_url(self):
        # http://hlsaudio-akc.med2.med.nhl.com/ls04/nhl/2017/12/31/NHL_GAME_AUDIO_TORVGK_M2_VISIT_20171231_1513799214035/master_radio.m3u8
        pass
