"""
Models the game data retrieved via JSON.
"""

import logging
import pprint
import time

from datetime import datetime
from datetime import timedelta
from dateutil import parser

import mlbv.mlbam.common.config as config
import mlbv.mlbam.common.gamedata as gamedata
import mlbv.mlbam.common.util as util
import mlbv.mlbam.common.displayutil as displayutil

from mlbv.mlbam.common.displayutil import ANSI


LOG = logging.getLogger(__name__)


TEAM_CODES = ('ari', 'atl', 'bal', 'bos', 'chc', 'cws', 'cin', 'cle', 'col', 'det', 'fla', 'hou', 'kan', 'laa', 'lad',
              'mil', 'min', 'nym', 'nyy', 'oak', 'phi', 'pit', 'sd', 'sf', 'sea', 'stl', 'tb', 'tex', 'tor', 'wsh')

FILTERS = {
    'favs': '',  # is filled out by config parser
    'ale': 'bal,bos,nyy,tb,tor',
    'alc': 'cle,cws,det,kan,min',
    'alw': 'hou,laa,oak,sea,tex',
    'nle': 'atl,fla,nym,phi,wsh',
    'nlc': 'chc,cin,mil,pit,stl,',
    'nlw': 'ari,col,lad,sd,sf',
}
FILTERS['al'] = '{},{},{}'.format(FILTERS['ale'], FILTERS['alc'], FILTERS['alw'])
FILTERS['nl'] = '{},{},{}'.format(FILTERS['nle'], FILTERS['nlc'], FILTERS['nlw'])


# this map is used to transform the statsweb feed name to something shorter
FEEDTYPE_MAP = {
    'away': 'a',
    'home': 'h',
    'french': 'fr',
    'national': 'nat',
    'in_market_away': 'ima',
    'in_market_home': 'imh',
    'condensed': 'cnd',
    'recap': 'rcp',
    # 'audio-away': 'aud-a',
    # 'audio-home': 'aud-h',
}


class GameDataRetriever:
    """Retrieves and parses game data from statsapi.mlb.com"""

    def _get_games_by_date(self, date_str=None):
        if date_str is None:
            date_str = time.strftime("%Y-%m-%d")

        # https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2018-03-26&endDate=2018-03-26&hydrate=schedule.teams,schedule.linescore,schedule.game.content.media.epg
        # hydrate = 'hydrate=schedule.teams,schedule.linescore,schedule.game.content.media.epg'
        hydrate = 'hydrate=broadcasts(all),game(content(all)),linescore,team'
        # hydrate = 'hydrate=linescore,team,game(content(summary,media(epg)),tickets)'
        url = '{0}/api/v1/schedule?sportId=1&startDate={1}&endDate={1}&{2}'.format(config.CONFIG.parser['api_url'], date_str, hydrate)

        json_data = util.request_json(url, 'gamedata')

        game_records = dict()  # we return this dictionary

        if json_data['dates'] is None or len(json_data['dates']) < 1:
            LOG.debug("_get_games_by_date: no game data for %s", date_str)
            return None

        for game in json_data['dates'][0]['games']:
            # LOG.debug('game: {}'.format(game))
            game_pk_str = str(game['gamePk'])
            game_records[game_pk_str] = dict()
            game_rec = game_records[game_pk_str]
            game_rec['game_pk'] = game_pk_str

            game_rec['abstractGameState'] = str(game['status']['abstractGameState'])  # Preview, Live, Final
            game_rec['codedGameState'] = str(game['status']['codedGameState'])  # is something like: F, O, C, I
            # is something like: Scheduled, Live, Final, In Progress, Critical, Postponed:
            game_rec['detailedState'] = str(game['status']['detailedState'])
            game_rec['doubleHeader'] = str(game['doubleHeader'])
            game_rec['gameNumber'] = str(game['gameNumber'])
            game_rec['mlbdate'] = parser.parse(str(game['gameDate']))
            if 'gamesInSeries' in game:
                game_rec['gamesInSeries'] = str(game['gamesInSeries'])
                game_rec['seriesGameNumber'] = str(game['seriesGameNumber'])
            else:
                game_rec['gamesInSeries'] = "0"
                game_rec['seriesGameNumber'] = "0"

            game_rec['linescore'] = dict()
            if 'linescore' in game:
                game_rec['linescore']['raw'] = game['linescore']
                if 'Delayed' in game_rec['detailedState']:
                    game_rec['linescore']['currentInning'] = str(game_rec['detailedState'])
                    game_rec['linescore']['currentInningOrdinal'] = 'Not Started'
                    game_rec['linescore']['inningState'] = ''
                elif 'currentInning' in game['linescore']:
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

            game_rec['favourite'] = gamedata.is_fav(game_rec)

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
                                    if playback_item['name'] == config.CONFIG.parser['playback_scenario']:
                                        game_rec['feed'][feedtype]['playback_url'] = playback_item['url']
                        elif media['title'] == 'Daily Recap':
                            feedtype = 'recap'
                            if len(media['items']) > 0:
                                game_rec['feed'][feedtype] = dict()
                                stream = media['items'][0]
                                game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaPlaybackId'])
                                for playback_item in stream['playbacks']:
                                    if playback_item['name'] == config.CONFIG.parser['playback_scenario']:
                                        game_rec['feed'][feedtype]['playback_url'] = playback_item['url']
                        # elif media['title'] == 'Audio':
                        #     for stream in media['items']:
                        #         feedtype = 'audio-' + str(stream['mediaFeedType']).lower()  # home, away, national, french, ...
                        #         game_rec['feed'][feedtype] = dict()
                        #         game_rec['feed'][feedtype]['mediaPlaybackId'] = str(stream['mediaId'])
                        #         game_rec['feed'][feedtype]['eventId'] = str(stream['id'])
                        #         game_rec['feed'][feedtype]['callLetters'] = str(stream['callLetters'])

        return game_records

    def get_audio_stream_url(self):
        # http://hlsaudio-akc.med2.med.nhl.com/ls04/nhl/2017/12/31/NHL_GAME_AUDIO_TORVGK_M2_VISIT_20171231_1513799214035/master_radio.m3u8
        pass

    def process_game_data(self, game_date, num_days=1):
        game_days_list = list()
        for i in range(0, num_days):
            game_records = self._get_games_by_date(game_date)
            if game_records is not None:
                game_days_list.append((game_date, game_records))
            game_date = datetime.strftime(datetime.strptime(game_date, "%Y-%m-%d") + timedelta(days=1), "%Y-%m-%d")
        return game_days_list


class GameDatePresenter:
    """Formats game data for CLI output."""

    def __get_feeds_for_display(self, game_rec):
        non_highlight_feeds = list()
        use_short_feeds = config.CONFIG.parser.getboolean('use_short_feeds', True)
        for feed in sorted(game_rec['feed'].keys()):
            if feed not in config.HIGHLIGHT_FEEDTYPES and not feed.startswith('audio-'):
                if use_short_feeds:
                    non_highlight_feeds.append(gamedata.convert_feedtype_to_short(feed, FEEDTYPE_MAP))
                else:
                    non_highlight_feeds.append(feed)
        highlight_feeds = list()
        for feed in game_rec['feed'].keys():
            if feed in config.HIGHLIGHT_FEEDTYPES and not feed.startswith('audio-'):
                if use_short_feeds:
                    highlight_feeds.append(gamedata.convert_feedtype_to_short(feed, FEEDTYPE_MAP))
                else:
                    highlight_feeds.append(feed)
        if len(highlight_feeds) > 0:
            return '{} {}'.format(','.join(non_highlight_feeds), ','.join(highlight_feeds))
        return '{}'.format(','.join(non_highlight_feeds))

    def display_game_data(self, game_date, game_records, filter):
        show_scores = config.CONFIG.parser.getboolean('scores')
        show_linescore = config.CONFIG.parser.getboolean('linescore')
        border = displayutil.Border(use_unicode=config.UNICODE)
        if game_records is None:
            # outl.append("No game data for {}".format(game_date))
            LOG.info("No game data for {}".format(game_date))
            # LOG.info("No game data to display")
            return

        outl = list()  # holds list of strings for output
        print_outl = False

        # print header
        date_hdr = '{:7}{} {}'.format('', game_date, datetime.strftime(datetime.strptime(game_date, "%Y-%m-%d"), "%a"))
        if show_scores:
            if show_linescore:
                outl.append("{:56}".format(date_hdr))
                outl.append('{c_on}{dash}{c_off}'
                            .format(c_on=border.border_color, dash=border.thickdash*91, c_off=border.color_off))
            else:
                outl.append("{:48} {:^7} {pipe} {:^5} {pipe} {:^9} {pipe} {}"
                            .format(date_hdr, 'Series', 'Score', 'State', 'Feeds', pipe=border.pipe))
                outl.append("{c_on}{}{pipe}{}{pipe}{}{pipe}{}{c_off}"
                            .format(border.thickdash * 57, border.thickdash * 7, border.thickdash * 11, border.thickdash * 16,
                                    pipe=border.junction, c_on=border.border_color, c_off=border.color_off))
        else:
            outl.append("{:48} {:^7} {pipe} {:^9} {pipe} {}".format(date_hdr, 'Series', 'State', 'Feeds', pipe=border.pipe))
            outl.append("{c_on}{}{pipe}{}{pipe}{}{c_off}"
                        .format(border.thickdash * 57, border.thickdash * 11, border.thickdash * 16,
                                pipe=border.junction, c_on=border.border_color, c_off=border.color_off))

        games_displayed_count = 0
        for game_pk in game_records:
            if gamedata.apply_filter(game_records[game_pk], filter, FILTERS) is not None:
                games_displayed_count += 1
                outl.extend(self._display_game_details(game_pk, game_records[game_pk], show_linescore,
                                                       games_displayed_count))
                print_outl = True

        if print_outl:
            print('\n'.join(outl))

    def _display_game_details(self, game_pk, game_rec, show_linescore, games_displayed_count):
        show_scores = config.CONFIG.parser.getboolean('scores')
        outl = list()
        border = displayutil.Border(use_unicode=config.UNICODE)
        color_on = ''
        color_off = ''
        # odd_even = games_displayed_count % 2
        # if odd_even:
        #     color_on = ANSI.fg('yellow')
        # else:
        #     color_on = display'reset'.ANSI.fg('lightblue')
        color_off = ANSI.reset()
        if gamedata.is_fav(game_rec):
            if config.CONFIG.parser['fav_colour'] != '':
                color_on = ANSI.fg(config.CONFIG.parser['fav_colour'])
                color_off = ANSI.reset()
        if game_rec['abstractGameState'] == 'Live':
            color_on += ANSI.control_code('bold')
            color_off = ANSI.reset()
        if game_rec['doubleHeader'] == 'N':
            series_info = "{sgn}/{gis}".format(sgn=game_rec['seriesGameNumber'], gis=game_rec['gamesInSeries'])
        else:
            # series_info = "DH{gn} {sgn}/{gis}".format(sgn=game_rec['seriesGameNumber'],
            #                                           gis=game_rec['gamesInSeries'],
            #                                           gn=game_rec['gameNumber'])
            series_info = "DH-{gn}".format(gn=game_rec['gameNumber'])
        game_info_str = "{time}: {a1} ({a2}) at {h1} ({h2})"\
            .format(time=util.convert_time_to_local(game_rec['mlbdate']),
                    a1=game_rec['away']['display'], a2=game_rec['away']['abbrev'].upper(),
                    h1=game_rec['home']['display'], h2=game_rec['home']['abbrev'].upper())
        game_state = ''
        game_state_color_on = color_on
        game_state_color_off = color_off

        if game_rec['abstractGameState'] in ('Preview', ):
            if game_rec['detailedState'] != 'Scheduled':
                if 'Delayed' in game_rec['detailedState']:
                    game_state = 'Delayed'
                else:
                    game_state = game_rec['detailedState']
        else:
            if show_scores:
                if game_rec['detailedState'] in ('Critical', ):
                    game_state_color_on = ANSI.fg(config.CONFIG.parser['game_critical_colour'])
                    game_state_color_off = ANSI.reset()
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

        if show_scores:
            score = ''
            if game_rec['abstractGameState'] not in ('Preview', ) and game_rec['detailedState'] not in ('Postponed', ):
                score = '{}-{}'.format(game_rec['linescore']['away']['runs'], game_rec['linescore']['home']['runs'])

            # linescore
            if show_linescore:
                if games_displayed_count > 1:
                    outl.append('{coloron}{dash}{coloroff}'.format(coloron=ANSI.fg('darkgrey'),
                                                                   dash=border.dash*91,
                                                                   coloroff=ANSI.reset()))
                linescore_dict = self._format_linescore(game_rec)
                """
                18:05: LA Dodgers (LAD) at San Francisco (SF)            1  2  3  4  5  6  7  8  9 10 11 12 13 14  R  H  E
                1/2    Final(14): 5-7                              LAD   0  0  1  0  0  2  1  0  0  0  0  0  0  1  5 12  0
                       Feeds: a,h / cnd,rcp                        SF    1  0  0  2  0  1  0  0  0  0  0  0  0  3  7 17  1
                """
                line_fmt = "{coloron}{ginfo:<50} {lscore}{coloroff}"
                # if game_rec['abstractGameState'] not in ('Live', 'Final'):  # or game_rec['detailedState'] in ('Postponed', ):
                #     outl.append(line_fmt.format(coloron=color_on, coloroff=color_off, ginfo=game_info_str, lscore=''))
                #     return outl

                outl.append(line_fmt.format(coloron=color_on, coloroff=color_off,
                                            ginfo=game_info_str, lscore=linescore_dict['header'], pipe=border.pipe))
                if game_state == '':
                    # game_info_str = '{series:7}Not Started'.format(series=series_info)
                    game_info_str = '{series:7}'.format(series=series_info)
                else:
                    if game_rec['abstractGameState'] in ('Live',) \
                            and game_rec['linescore']['inningState'] != 'Mid' and 'raw' in game_rec['linescore']:
                        outs_info = ', {} out'.format(game_rec['linescore']['raw']['outs'])
                    else:
                        outs_info = ''
                    if score:
                        game_info_str = '{series:7}{gstate}: {score}{outs}'.format(series=series_info,
                                                                                   gstate=game_state, score=score, outs=outs_info)
                    else:
                        game_info_str = '{series:7}{gstate}'.format(series=series_info, gstate=game_state)
                outl.append(line_fmt.format(coloron=color_on, coloroff=color_off,
                                            ginfo=game_info_str, lscore=linescore_dict['away']))

                feeds = self.__get_feeds_for_display(game_rec)
                if feeds:
                    game_info_str = '{:7}Feeds: {feeds}'.format('', feeds=self.__get_feeds_for_display(game_rec))
                    outl.append(line_fmt.format(coloron=color_on, coloroff=color_off,
                                                ginfo=game_info_str, lscore=linescore_dict['home']))
                else:
                    outl.append(line_fmt.format(coloron=color_on, coloroff=color_off,
                                                ginfo='', lscore=linescore_dict['home']))
            else:
                # single-line game score
                outl.append(("{coloron}{ginfo:<48} {series:^7}{coloroff} "
                             "{pipe} {coloron}{score:^5}{coloroff} {pipe} "
                             "{gscoloron}{gstate:<9}{gscoloroff} {pipe} {coloron}{feeds}{coloroff}")
                            .format(coloron=color_on, coloroff=color_off,
                                    ginfo=game_info_str, series=series_info, score=score,
                                    gscoloron=game_state_color_on, gstate=game_state, gscoloroff=game_state_color_off,
                                    feeds=self.__get_feeds_for_display(game_rec), pipe=border.pipe))
        else:  # no scores
            outl.append(("{coloron}{ginfo:<48} {series:^7}{coloroff} {pipe} "
                         "{coloron}{gstate:^9}{coloroff} {pipe} {coloron}{feeds}{coloroff}")
                        .format(coloron=color_on, coloroff=color_off,
                                ginfo=game_info_str, series=series_info, gstate=game_state,
                                feeds=self.__get_feeds_for_display(game_rec), pipe=border.pipe))
        return outl

    def _format_linescore(self, game_rec):
        """Returns a dictionary indexed by keys: 'header', 'away', 'home'
             1  2  3  4  5  6  7  8  9 10 11  R  H  E
        TOR  1  0  0  0  0  0  0  3  0  0  0  4  8  0
        NYY  0  0  0  0  1  0  0  0  4  0  0  5  8  0
        """
        if 'raw' in game_rec['linescore']:
            linescore_json = game_rec['linescore']['raw']
        else:
            return {'header': '', 'away': '', 'home': ''}
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
