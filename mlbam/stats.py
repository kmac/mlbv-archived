"""
Future: parse https://statsapi.web.nhl.com/api/v1/standings

Help: see https://github.com/dword4/nhlapi#standing
"""

import logging
import os
import requests
import sys

import mlbam.auth as auth
import mlbam.util as util
import mlbam.config as config


LOG = logging.getLogger(__name__)

LEAGUE_ID_MAP = {
    'american': 103,
    'al': 103,
    'national': 104,
    'nl': 104,
}

#https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2017&standingsTypes=regularSeason&hydrate=division,conference,sport,league,team
#https://statsapi.mlb.com/api/v1/standings/regularSeason?leagueId=103,104&season=2018
STANDINGS_URL = ('https://statsapi.mlb.com/api/v1/standings/{standings_type}?'
                 'leagueId={league_ids}&season={season}&hydrate=division,conference,sport,league,team')

# from https://statsapi.mlb.com/api/v1/standingsTypes
STANDINGS_TYPES = ('regularSeason', 'wildCard', 'divisionLeaders', 'wildCardWithLeaders',
                   'firstHalf', 'secondHalf', 'springTraining', 'postseason',
                   'byDivision', 'byConference', 'byLeague')

STANDINGS_OPTIONS = ('all', 'division', 'conference', 'wildcard', 'league', 'postseason', 'preseason')

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
    return TEAMS_TO_FAVS[long_team_name] in util.get_csv_list(config.CONFIG.parser['favs'])


def _match(input_option, full_option, min_chars=2):
    num_chars = len(input_option)
    return input_option[:num_chars] == full_option[:num_chars]


def get_standings(standings_option='all'):
    if _match(standings_option, 'all') or _match(standings_option, 'division'):
        display_standings('byDivision', 'Division', header_tags=('division' ,))
        _match(standings_option, 'all') and print('')
    if _match(standings_option, 'all') or _match(standings_option, 'wildcard'):
        display_standings('wildCard', 'Wildcard', rank_tag='wildCardRank', header_tags=('league', ))
        _match(standings_option, 'all') and print('')
    if _match(standings_option, 'all') or _match(standings_option, 'overall') \
            or _match(standings_option, 'league') or _match(standings_option, 'conference'):
        display_standings('byLeague', 'League', rank_tag='leagueRank', header_tags=('league', ))
        _match(standings_option, 'all') and print('')

    if _match(standings_option, 'playoff') or _match(standings_option, 'postseason'):
        display_standings('postseason', 'Playoffs')
    if _match(standings_option, 'preseason'):
        display_standings('preseason', 'Preseason')


def display_standings(standings_type='byDivision', display_title='', rank_tag='divisionRank', header_tags=('league', 'division')):
    headers = {
        'User-Agent': config.CONFIG.ua_iphone,
        'Connection': 'close'
    }
    url = STANDINGS_URL.format(standings_type=standings_type, league_ids='103,104', season='2018')
    util.log_http(url, 'get', headers, sys._getframe().f_code.co_name)
    resp = requests.get(url, headers=headers, verify=config.VERIFY_SSL)

    json_file = os.path.join(config.CONFIG.dir, 'standings.json')
    with open(json_file, 'w') as f:  # write date to json_file
        f.write(resp.text)
    json_data = resp.json()

    outl = list()
    if display_title != '':
        # outl.append('   ========  {}  ========'.format(display_title))
        outl.append('{color_on}{name:22}\t{win:>3} {loss:>3} {pct:<5} {gb:<4} {wgb:<4} {streak}{color_off}'
                    .format(color_on='', name='   ========  {}  ========'.format(display_title),
                            win='W', loss='L', pct='PCT', gb='GB', wgb='WGB', streak='Streak', color_off=''))
    needs_line_hr = False
    for record in json_data['records']:
        if standings_type == record['standingsType']:
            if needs_line_hr > 0:
                pass
                # outl.append('-' * 10)
            header = ''
            for tag in header_tags:
                if tag in record:
                    if 'name' in record[tag]:
                        header = _add_to_header(header, record[tag]['name'])
                    else:
                        header = _add_to_header(header, record[tag])
            if header:
                header = '--- ' + header + ' ---'
                outl.append('   {}'.format(header))
                needs_line_hr = True
        else:
            LOG.error('Unexpected: standingsType=%s, not %s', record['standingsType'], standings_type)
        for teamrec in record['teamRecords']:
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
                    color_on = util.fg_ansi_colour(config.CONFIG.parser['fav_colour'])
                    color_off = util.ANSI_CONTROL_CODES['reset']
            outl.append('{color_on}{rank:2} {clinch}{name:22}\t{win:3} {loss:3} {pct:5} {gb:4} {wgb:4} [{streak}]{color_off}'
                        .format(color_on=color_on, rank=rank, clinch=clinch, name=teamrec['team']['name'],
                                win=teamrec['leagueRecord']['wins'],
                                loss=teamrec['leagueRecord']['losses'],
                                pct=teamrec['leagueRecord']['pct'],
                                gb=teamrec['gamesBack'],
                                wgb=teamrec['wildCardGamesBack'],
                                streak=teamrec['streak']['streakCode'],
                                color_off=color_off))
    print('\n'.join(outl))


def _add_to_header(header, text):
    if header:
        return header + ' - ' + text
    return text
