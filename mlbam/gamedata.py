"""
Models the game data retrieved via JSON.
"""

import logging
import pprint
import time

from datetime import datetime
from datetime import timedelta
from dateutil import parser

import mlbam.config as config
import mlbam.util as util


LOG = logging.getLogger(__name__)


TEAM_CODES = ('ari', 'atl', 'bal', 'bos', 'chc', 'cws', 'cin', 'cle', 'col', 'det', 'fla', 'hou', 'kan', 'laa', 'lad',
              'mil', 'min', 'nym', 'nyy', 'oak', 'phi', 'pit', 'sd', 'sf', 'sea', 'stl', 'tb', 'tex', 'tor', 'wsh')


# this map is used to transform the statsweb feed name to something shorter
FEEDTYPE_MAP = {
    'away': 'a',
    'home': 'h',
    'french': 'fr',
    'national': 'nat',
    'in_market_away': 'mkt_a',
    'in_market_home': 'mkt_h',
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


def convert_feedtype_to_short(feedtype):
    if feedtype in FEEDTYPE_MAP:
        return FEEDTYPE_MAP[feedtype]
    return feedtype


def convert_to_long_feedtype(feed):
    if feed in FEEDTYPE_MAP:
        return feed
    for feedtype in FEEDTYPE_MAP:
        if FEEDTYPE_MAP[feedtype] == feed:
            return feedtype
    return feed


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

    def __init__(self):
        self.game_data_list = list()

    def __get_feeds_for_display(self, game_rec):
        non_highlight_feeds = list()
        use_short_feeds = config.CONFIG.parser.getboolean('use_short_feeds', True)
        for feed in sorted(game_rec['feed'].keys()):
            if feed not in config.HIGHLIGHT_FEEDTYPES and not feed.startswith('audio-'):
                if use_short_feeds:
                    non_highlight_feeds.append(convert_feedtype_to_short(feed))
                else:
                    non_highlight_feeds.append(feed)
        highlight_feeds = list()
        for feed in game_rec['feed'].keys():
            if feed in config.HIGHLIGHT_FEEDTYPES and not feed.startswith('audio-'):
                if use_short_feeds:
                    highlight_feeds.append(convert_feedtype_to_short(feed))
                else:
                    highlight_feeds.append(feed)
        return '{:7} {}'.format('/'.join(non_highlight_feeds), '/'.join(highlight_feeds))

    def _get_game_data(self, date_str=None, overwrite_json=True):
        if date_str is None:
            date_str = time.strftime("%Y-%m-%d")

        # https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2018-03-26&endDate=2018-03-26&hydrate=schedule.teams,schedule.linescore,schedule.game.content.media.epg
        # hydrate = 'hydrate=schedule.teams,schedule.linescore,schedule.game.content.media.epg'
        hydrate = 'hydrate=broadcasts(all),game(content(all)),linescore,team'
        # hydrate = 'hydrate=linescore,team,game(content(summary,media(epg)),tickets)'
        url = '{0}/api/v1/schedule?sportId=1&startDate={1}&endDate={1}&{2}'.format(config.CONFIG.api_url, date_str, hydrate)

        json_data = util.request_json(url, 'gamedata')

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
            # is something like: Scheduled, Live, Final, In Progress, Critical, Postponed:
            game_rec['detailedState'] = str(game['status']['detailedState'])
            game_rec['doubleHeader'] = str(game['doubleHeader'])
            game_rec['gameNumber'] = str(game['gameNumber'])
            game_rec['mlbdate'] = parser.parse(str(game['gameDate']))
            game_rec['gamesInSeries'] = str(game['gamesInSeries'])
            game_rec['seriesGameNumber'] = str(game['seriesGameNumber'])

            game_rec['linescore'] = dict()
            if 'linescore' in game:
                game_rec['linescore']['raw'] = game['linescore']
                if 'currentInning' in game['linescore']:
                    game_rec['linescore']['currentInning'] = str(game['linescore']['currentInning'])
                else:
                    game_rec['linescore']['currentInningOrdinal'] = '0'
                if 'currentInningOrdinal' in game['linescore']:
                    game_rec['linescore']['currentInningOrdinal'] = str(game['linescore']['currentInningOrdinal'])
                    if 'inningState' in game['linescore']:
                        game_rec['linescore']['inningState'] = str(game['linescore']['inningState'])[:3]
                    else:
                        game_rec['linescore']['inningState'] = str(game['linescore']['inningHalf'])[:3]
                else:
                    game_rec['linescore']['currentInningOrdinal'] = 'Not Started'
                    game_rec['linescore']['inningState'] = ''
            else:
                game_rec['linescore']['currentInning'] = 'n/a'
                game_rec['linescore']['inningState'] = ''
                game_rec['linescore']['currentInningOrdinal'] = game_rec['detailedState']

            for teamtype in ('home', 'away'):
                # pprint.pprint(game['teams'])
                game_rec[teamtype] = dict()
                # seems to be two different formats for away/home team info(!)
                if 'name' in game['teams'][teamtype]['team'] and 'abbrev' in game['teams'][teamtype]['team']['name']:
                    game_rec[teamtype] = {
                        'abbrev':   str(game['teams'][teamtype]['team']['name']['abbrev']).lower(),
                        'display':  str(game['teams'][teamtype]['team']['name']['display']),
                        'brief':    str(game['teams'][teamtype]['team']['name']['brief']),
                        'full':     str(game['teams'][teamtype]['team']['name']['full']),
                        'league':   str(game['teams'][teamtype]['league']),
                        'division': str(game['teams'][teamtype]['division']),
                    }
                elif 'abbreviation' in game['teams'][teamtype]['team']:
                    game_rec[teamtype] = {
                        'abbrev':   str(game['teams'][teamtype]['team']['abbreviation']).lower(),
                        'display':  str(game['teams'][teamtype]['team']['shortName']),
                        'brief':    str(game['teams'][teamtype]['team']['teamName']),
                        'full':     str(game['teams'][teamtype]['team']['name']),
                        'league':   'n/a',
                        'division': 'n/a',
                    }
                else:
                    LOG.error("Unexpected game['teams'] for teamtype=%s", teamtype)
                    pprint.pprint(game['teams'][teamtype])
                    game_rec[teamtype] = {
                        'abbrev': 'n/a', 'display': 'n/a', 'brief': 'n/a', 'full': 'n/a', 'league': 'n/a', 'division': 'n/a',
                    }

                if 'linescore' in game and teamtype in game['linescore']['teams'] and 'runs' in game['linescore']['teams'][teamtype]:
                    game_rec['linescore'][teamtype] = {
                        'runs':  str(game['linescore']['teams'][teamtype]['runs']),
                        'hits':  str(game['linescore']['teams'][teamtype]['hits']),
                        'errors': str(game['linescore']['teams'][teamtype]['errors']),
                    }
                else:
                    game_rec['linescore'][teamtype] = {'runs':  '0', 'hits':  '0', 'errors': '0'}

            game_rec['favourite'] = is_fav(game_rec)

            game_rec['feed'] = dict()
            if game_rec['abstractGameState'] == 'Preview':
                continue

            # epg
            if 'media' in game['content'] and 'epg' in game['content']['media']:
                for media in game['content']['media']['epg']:
                    if media['title'] == 'MLBTV':
                        for stream in media['items']:
                            if stream['mediaFeedType'] != 'COMPOSITE' and stream['mediaFeedType'] != 'ISO':
                                feedtype = str(stream['mediaFeedType']).lower()  # home, away, national, french, ...
                                game_rec['feed'][feedtype] = dict()
                                if 'mediaId' in stream:
                                    game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaId'])
                                    game_rec['feed'][feedtype]['mediaState'] = str(stream['mediaState'])
                                    game_rec['feed'][feedtype]['eventId'] = str(stream['id'])
                                    game_rec['feed'][feedtype]['callLetters'] = str(stream['callLetters'])
                if 'epgAlternate' in game['content']['media']:
                    for media in game['content']['media']['epgAlternate']:
                        if media['title'] == 'Extended Highlights':
                            feedtype = 'condensed'
                            if len(media['items']) > 0:
                                game_rec['feed'][feedtype] = dict()
                                stream = media['items'][0]
                                game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaPlaybackId'])
                                for playback_item in stream['playbacks']:
                                    if playback_item['name'] == config.CONFIG.playback_scenario:
                                        game_rec['feed'][feedtype]['playback_url'] = playback_item['url']
                        elif media['title'] == 'Daily Recap':
                            feedtype = 'recap'
                            if len(media['items']) > 0:
                                game_rec['feed'][feedtype] = dict()
                                stream = media['items'][0]
                                game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaPlaybackId'])
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

    def retrieve_and_display_game_data(self, game_date, num_days=1, show_games=True):
        game_data_list = list()
        show_scores = config.CONFIG.parser.getboolean('scores')
        show_linescore = config.CONFIG.parser.getboolean('linescore')
        for i in range(0, num_days):
            game_data = self._get_game_data(game_date)
            outl = list()  # holds list of strings for output
            print_outl = False
            if game_data is not None:
                game_data_list.append(game_data)
                if not show_games:
                    continue

                # print header
                date_hdr = '{:7}{}'.format('', '{}'.format(game_date))
                if show_scores:
                    outl.append("{:56} {:^7} | {:^5} | {:^9} | {}".format(date_hdr, 'Series', 'Score', 'State', 'Feeds'))
                    outl.append("{}|{}|{}|{}".format('-' * 65, '-' * 7, '-' * 11, '-' * 14))
                else:
                    outl.append("{:56} {:^7} | {:^9} | {}".format(date_hdr, 'Series', 'State', 'Feeds'))
                    outl.append("{}|{}|{}".format('-' * 65, '-' * 11, '-' * 12))

                for game_pk in game_data:
                    if True or game_data[game_pk]['abstractGameState'] != 'Live':
                        if filter_favs(game_data[game_pk]) is not None:
                            outl.extend(self.display_game_details(game_pk, game_data[game_pk], show_linescore))
                            print_outl = True
            else:
                outl.append("No game data for {}".format(game_date))
                print_outl = True
            if print_outl:
                print('\n'.join(outl))
                if num_days > 1:
                    print('')  # add line feed between days

            game_date = datetime.strftime(datetime.strptime(game_date, "%Y-%m-%d") + timedelta(days=1), "%Y-%m-%d")

        return game_data_list

    def display_game_details(self, game_pk, game_rec, show_linescore):
        outl = list()
        color_on = ''
        color_off = ''
        if is_fav(game_rec):
            if config.CONFIG.parser['fav_colour'] != '':
                color_on = util.fg_ansi_colour(config.CONFIG.parser['fav_colour'])
                color_off = util.ANSI_CONTROL_CODES['reset']
        show_scores = config.CONFIG.parser.getboolean('scores')
        if game_rec['doubleHeader'] == 'N':
            series_info = "{sgn}/{gis}".format( sgn=game_rec['seriesGameNumber'], gis=game_rec['gamesInSeries'])
        else:
            series_info = "DH{gn} {sgn}/{gis}".format(sgn=game_rec['seriesGameNumber'],
                                                      gis=game_rec['gamesInSeries'],
                                                      gn=game_rec['gameNumber'])
        game_info_str = "{time}: {a1} ({a2}) at {h1} ({h2})"\
            .format(time=util.convert_time_to_local(game_rec['mlbdate']),
                    a1=game_rec['away']['display'], a2=game_rec['away']['abbrev'].upper(),
                    h1=game_rec['home']['display'], h2=game_rec['home']['abbrev'].upper())
        # if game_rec['doubleHeader'] != 'N':
        #     game_info_str = "{ginfo:<57}{dh}".format(ginfo=game_info_str, dh=doubleheader_info)
        game_state = ''
        game_state_color_on = color_on
        game_state_color_off = color_off
        # LOG.debug("Checking game state: %s, %s", game_rec['abstractGameState'], game_rec['detailedState'])
        if game_rec['abstractGameState'] not in ('Preview', ):
            if show_scores:
                if 'Critical' in game_rec['detailedState']:
                    game_state_color_on = util.fg_ansi_colour(config.CONFIG.parser['game_critical_colour'])
                    game_state_color_off = util.ANSI_CONTROL_CODES['reset']
                if game_rec['detailedState'] in ('Final', ):
                    game_state = game_rec['detailedState']
                    if 'currentInning' in game_rec['linescore'] and int(game_rec['linescore']['currentInning']) != 9:
                        game_state += '({})'.format(game_rec['linescore']['currentInning'])
                else:
                    if game_rec['linescore']['inningState'] != '':
                        game_state = '{} {}'.format(game_rec['linescore']['inningState'].title(),
                                                    game_rec['linescore']['currentInningOrdinal'])
                    else:
                        game_state = game_rec['linescore']['currentInningOrdinal']
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
            if show_linescore and game_rec['abstractGameState'] not in ('Preview', ) and \
                    'raw' in game_rec['linescore'] and game_rec['linescore']['raw']['innings']:
                linescore_dict = self.get_linescore_dict(game_rec)
                outl.append(("{coloron}{ginfo:<56} {series:^7}{coloroff} | {coloron}{score:^5}{coloroff} | "
                             "{gscoloron}{gstate:^9}{gscoloroff} | {coloron}{feeds}{coloroff}")
                            .format(coloron=color_on, coloroff=color_off,
                                    ginfo=game_info_str, series=series_info, score=score,
                                    gscoloron=game_state_color_on, gstate=game_state,
                                    gscoloroff=game_state_color_off, feeds=self.__get_feeds_for_display(game_rec)))
                game_info_str = '{:3}{}'.format('', linescore_dict['header'])
                if game_rec['abstractGameState'] in ('Live',) and game_rec['linescore']['inningState'] != 'Mid':
                    # score_field = '{}-{} {} out'.format(game_rec['linescore']['raw']['balls'],
                    #                                     game_rec['linescore']['raw']['strikes'],
                    #                                     game_rec['linescore']['raw']['outs'])
                    score_field = '{} out'.format(game_rec['linescore']['raw']['outs'])
                else:
                    score_field = ''
                outl.append(("{coloron}{ginfo:<63} {coloroff} | {coloron}{score:^5}{coloroff} | "
                             "{gscoloron}{gstate:^9}{gscoloroff} | {coloron}{feeds}{coloroff}")
                            .format(coloron=color_on, coloroff=color_off,
                                    ginfo=game_info_str, score='', gscoloron=game_state_color_on,
                                    gstate=score_field, gscoloroff=game_state_color_off, feeds=''))
                for team in ('away', 'home'):
                    game_info_str = '{:3}{}'.format('', linescore_dict[team])
                    outl.append(("{coloron}{ginfo:<63} {coloroff} | {coloron}{score:^5}{coloroff} | "
                                 "{gscoloron}{gstate:^9}{gscoloroff} | {coloron}{feeds}{coloroff}")
                                .format(coloron=color_on, coloroff=color_off,
                                        ginfo=game_info_str, score='', gscoloron=game_state_color_on,
                                        gstate='', gscoloroff=game_state_color_off, feeds=''))
            else:
                outl.append(("{coloron}{ginfo:<56} {series:^7}{coloroff} | {coloron}{score:^5}{coloroff} | "
                             "{gscoloron}{gstate:^9}{gscoloroff} | {coloron}{feeds}{coloroff}")
                            .format(coloron=color_on, coloroff=color_off,
                                    ginfo=game_info_str,
                                    series=series_info,
                                    score=score,
                                    gscoloron=game_state_color_on,
                                    gstate=game_state,
                                    gscoloroff=game_state_color_off,
                                    feeds=self.__get_feeds_for_display(game_rec)))
        else:
            outl.append(("{coloron}{ginfo:<56} {series:^7}{coloroff} | "
                         "{coloron}{gstate:^9}{coloroff} | {coloron}{feeds}{coloroff}")
                        .format(coloron=color_on, coloroff=color_off,
                                ginfo=game_info_str,
                                series=series_info,
                                gstate=game_state,
                                feeds=self.__get_feeds_for_display(game_rec)))
        if config.CONFIG.parser.getboolean('debug') and config.CONFIG.parser.getboolean('verbose'):
            for feedtype in game_rec['feed']:
                outl.append('    {}: {}  [game_pk:{}, mediaPlaybackId:{}]'.format(feedtype,
                                                                                  game_rec['abstractGameState'],
                                                                                  game_pk,
                                                                                  game_rec['feed'][feedtype]['mediaPlaybackId']))
        return outl

    def get_linescore_dict(self, game_rec):
        """
             1  2  3  4  5  6  7  8  9 10 11  R  H  E
        TOR  1  0  0  0  0  0  0  3  0  0  0  4  8  0
        NYY  0  0  0  0  1  0  0  0  4  0  0  5  8  0

        Returns a dictionary for easy processing of home/away
        """
        linescore_json = game_rec['linescore']['raw']
        outd = dict()
        outd['header'] = '{title:<4}'.format(title='')
        outd['away'] = '{title:<4}'.format(title=game_rec['away']['abbrev'].upper())
        outd['home'] = '{title:<4}'.format(title=game_rec['home']['abbrev'].upper())
        if 'currentInning' in linescore_json:
            current_inning = int(linescore_json['currentInning'])
        else:
            current_inning = 0
        for inning in linescore_json['innings']:
            outd['header'] += '{:>3}'.format(inning['num'])
            for team in ('away', 'home'):
                if 'runs' in inning[team]:
                    outd[team] += '{:>3}'.format(inning[team]['runs'])
                else:
                    outd[team] += '{:>3}'.format('')
        for inning_num in range(current_inning+1, 10):  # fill in remaining innings, if any
            outd['header'] += '{:>3}'.format(inning_num)
            outd['away'] += '{:>3}'.format('')
            outd['home'] += '{:>3}'.format('')
        outd['header'] += '{:>3}{:>3}{:>3}'.format('R', 'H', 'E')
        for team in ('away', 'home'):
            if 'teams' in linescore_json and team in linescore_json['teams'] \
                    and 'runs' in linescore_json['teams'][team]:
                outd[team] += '{:>3}{:>3}{:>3}'.format(linescore_json['teams'][team]['runs'],
                                                       linescore_json['teams'][team]['hits'],
                                                       linescore_json['teams'][team]['errors'])
        return outd

    def get_audio_stream_url(self):
        # http://hlsaudio-akc.med2.med.nhl.com/ls04/nhl/2017/12/31/NHL_GAME_AUDIO_TORVGK_M2_VISIT_20171231_1513799214035/master_radio.m3u8
        pass
