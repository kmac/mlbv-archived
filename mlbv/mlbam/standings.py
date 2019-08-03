"""
Future: parse https://statsapi.web.nhl.com/api/v1/standings

Help: see https://github.com/dword4/nhlapi#standing
"""

import logging
import time

from datetime import datetime

import mlbv.mlbam.common.displayutil as displayutil
import mlbv.mlbam.common.config as config
import mlbv.mlbam.common.util as util

from mlbv.mlbam.common.displayutil import ANSI


LOG = logging.getLogger(__name__)

LEAGUE_ID_MAP = {
    'american': 103,
    'al': 103,
    'national': 104,
    'nl': 104,
}

STANDINGS_URL = ('https://statsapi.mlb.com/api/v1/standings/{standings_type}?'
                 'leagueId={league_ids}&season={season}{date}&hydrate=division,conference,sport,league,team')

# from https://statsapi.mlb.com/api/v1/standingsTypes
STANDINGS_TYPES = ('regularSeason', 'wildCard', 'divisionLeaders', 'wildCardWithLeaders',
                   'firstHalf', 'secondHalf', 'springTraining', 'postseason',
                   'byDivision', 'byConference', 'byLeague')

STANDINGS_OPTIONS = ('all', 'division', 'conference', 'wildcard', 'league', 'postseason', 'preseason')

LEAGUE_FILTERS = ('al', 'nl')
DIVISION_FILTERS = ('ale', 'alc', 'alw', 'nle', 'nlc', 'nlw')

# Converts the team names from standings json to abbreviations
TEAMS_TO_FAVS = {
    'Chicago White Sox': 'cws', 'Boston Red Sox': 'bos', 'Houston Astros': 'hou', 'Los Angeles Angels': 'laa',
    'New York Yankees': 'nyy', 'Cleveland Indians': 'cle', 'Minnesota Twins': 'min', 'Baltimore Orioles': 'bal',
    'Seattle Mariners': 'sea', 'Oakland Athletics': 'oak', 'Tampa Bay Rays': 'tb', 'Texas Rangers': 'tex',
    'Toronto Blue Jays': 'tor', 'Detroit Tigers': 'det', 'Kansas City Royals': 'kan', 'Milwaukee Brewers': 'mil',
    'New York Mets': 'nym', 'Washington Nationals': 'wsh', 'Arizona Diamondbacks': 'ari', 'San Francisco Giants': 'sf',
    'Pittsburgh Pirates': 'pit', 'Chicago Cubs': 'chc', 'Atlanta Braves': 'atl', 'Colorado Rockies': 'col',
    'Los Angeles Dodgers': 'lad', 'Miami Marlins': 'fla', 'Philadelphia Phillies': 'phi', 'Cincinnati Reds': 'cin',
    'St. Louis Cardinals': 'stl', 'San Diego Padres': 'sd',
}


def _is_fav(long_team_name):
    if long_team_name in TEAMS_TO_FAVS.keys():
        return TEAMS_TO_FAVS[long_team_name] in util.get_csv_list(config.CONFIG.parser['favs'])
    return False


def _match(input_option, full_option):
    num_chars = len(input_option)
    return input_option[:num_chars] == full_option[:num_chars]


def _add_to_header(header, text):
    if header:
        return header + ' - ' + text
    return text


def get_standings(standings_option='all', date_str=None, args_filter=None):
    """Displays standings."""
    LOG.debug('Getting standings for %s, option=%s', date_str, standings_option)
    if date_str == time.strftime("%Y-%m-%d"):
        # strip out date string from url (issue #5)
        date_str = None
    if _match(standings_option, 'all') or _match(standings_option, 'division'):
        display_division_standings(date_str, args_filter, rank_tag='divisionRank', header_tags=('league', 'division'))
        if _match(standings_option, 'all'):
            print('')
    if _match(standings_option, 'all') or _match(standings_option, 'wildcard'):
        _display_standings('wildCard', 'Wildcard', date_str, args_filter, rank_tag='wildCardRank', header_tags=('league', ))
        if _match(standings_option, 'all'):
            print('')
    if _match(standings_option, 'all') or _match(standings_option, 'overall') \
            or _match(standings_option, 'league') or _match(standings_option, 'conference'):
        _display_standings('byLeague', 'League', date_str, args_filter, rank_tag='leagueRank', header_tags=('league', ))
        if _match(standings_option, 'all'):
            print('')

    if _match(standings_option, 'playoff') or _match(standings_option, 'postseason'):
        _display_standings('postseason', 'Playoffs', date_str, args_filter)
    if _match(standings_option, 'preseason'):
        _display_standings('preseason', 'Preseason', date_str, args_filter)


def _get_title_header(display_title, border):
    name = '   {thickborder} {title} {thickborder}'.format(title=display_title,
                                                           thickborder=border.doubledash * int((29-len(display_title))/2 - 1))
    header = '{color_on}{name:31} {win:>3} {loss:>3} {pct:<5} {gb:<4} {wgb:<4} {streak}{color_off}'.format(
        color_on=border.border_color,
        name=name, win='W', loss='L', pct='PCT', gb='GB', wgb='WGB', streak='Streak',
        color_off=ANSI.reset())
    return header


def _get_subtitle_header(record, header_tags, border):
    header = ''
    for tag in header_tags:
        if tag in record:
            if 'name' in record[tag]:
                header = _add_to_header(header, record[tag]['name'])
            else:
                header = _add_to_header(header, record[tag])
    if header:
        header = '{color_on}{b1} {title} {b2}{color_off}'.format(color_on=border.border_color,
                                                                 title=header,
                                                                 b1=border.dash*3,
                                                                 b2=border.dash*(52-len(header)),
                                                                 color_off=ANSI.reset())
        return header
    return None


def _get_team_str(teamrec, rank_tag):
    clinch = ''
    if 'clinchIndicator' in teamrec:
        clinch = teamrec['clinchIndicator'] + '-'
    rank = ''
    if rank_tag in teamrec:
        rank = teamrec[rank_tag]
    color_on = ''
    color_off = ''
    if _is_fav(teamrec['team']['name']):
        if config.CONFIG.parser['fav_colour'] != '':
            color_on = ANSI.fg(config.CONFIG.parser['fav_colour'])
            color_off = ANSI.reset()
    name = clinch + teamrec['team']['name']
    return '{color_on}{rank:2} {name:28} {win:3} {loss:3} {pct:5} {gb:4} {wgb:4} [{streak}]{color_off}'.format(
        color_on=color_on, rank=rank, name=name,
        win=teamrec['leagueRecord']['wins'],
        loss=teamrec['leagueRecord']['losses'],
        pct=teamrec['leagueRecord']['pct'],
        gb=teamrec['gamesBack'],
        wgb=teamrec['wildCardGamesBack'],
        streak=teamrec['streak']['streakCode'],
        color_off=color_off)


def _get_standings_display_for_record(outl, standings_type, record, header_tags, rank_tag, border, needs_line_hr):
    if standings_type == record['standingsType']:
        if needs_line_hr > 0:
            pass
            # outl.append('-' * 10)

        # Display standings header
        header = _get_subtitle_header(record, header_tags, border)
        if header:
            outl.append('   {}'.format(header))
            needs_line_hr = True
    else:
        LOG.error('Unexpected: standingsType=%s, not %s', record['standingsType'], standings_type)

    for teamrec in record['teamRecords']:
        outl.append(_get_team_str(teamrec, rank_tag))


def _display_standings(standings_type, display_title, date_str, args_filter, rank_tag='divisionRank', header_tags=('league', 'division')):
    if date_str is None:
        season_str = time.strftime("%Y")
        url_date_str = ''
    else:
        season_str = datetime.strftime(datetime.strptime(date_str, "%Y-%m-%d"), "%Y")
        url_date_str = '&date=' + date_str
    url = STANDINGS_URL.format(standings_type=standings_type,
                               league_ids=_get_league_ids(args_filter),
                               season=season_str, date=url_date_str)
    json_data = util.request_json(url, 'standings')

    border = displayutil.Border(use_unicode=config.UNICODE)

    outl = list()
    if display_title != '':
        outl.append(_get_title_header(display_title, border))

    needs_line_hr = False
    for record in json_data['records']:
        if args_filter and standings_type == 'byDivision' and args_filter in DIVISION_FILTERS:
            pass

        _get_standings_display_for_record(outl, standings_type, record, header_tags, rank_tag, border, needs_line_hr)

    print('\n'.join(outl))


def _get_league_ids(args_filter):
    league_ids = '{},{}'.format(LEAGUE_ID_MAP['al'], LEAGUE_ID_MAP['nl'])
    if args_filter:
        if args_filter.startswith('al'):
            league_ids = LEAGUE_ID_MAP['al']
        elif args_filter.startswith('nl'):
            league_ids = LEAGUE_ID_MAP['nl']
    return league_ids


def _get_division_record(records, division_abbrev):
    for record in records:
        if str(record['division']['abbreviation']).lower() == division_abbrev:
            return record
    return None


def display_division_standings(date_str, args_filter, rank_tag='divisionRank', header_tags=('league', 'division')):
    standings_type = 'byDivision'
    display_title = 'Division'
    if date_str is None:
        season_str = time.strftime("%Y")
        url_date_str = ''
    else:
        season_str = datetime.strftime(datetime.strptime(date_str, "%Y-%m-%d"), "%Y")
        url_date_str = '&date=' + date_str
    url = STANDINGS_URL.format(standings_type=standings_type,
                               league_ids=_get_league_ids(args_filter),
                               season=season_str, date=url_date_str)
    json_data = util.request_json(url, 'standings')

    border = displayutil.Border(use_unicode=config.UNICODE)

    outl = list()
    if display_title != '':
        outl.append(_get_title_header(display_title, border))

    needs_line_hr = False
    if args_filter and args_filter in DIVISION_FILTERS:
        _get_standings_display_for_record(outl, standings_type,
                                          _get_division_record(json_data['records'], args_filter),
                                          header_tags, rank_tag, border, needs_line_hr)
    else:
        for div in DIVISION_FILTERS:
            div_record = _get_division_record(json_data['records'], div)
            if div_record:
                _get_standings_display_for_record(outl, standings_type, div_record,
                                                  header_tags, rank_tag, border, needs_line_hr)
    print('\n'.join(outl))
