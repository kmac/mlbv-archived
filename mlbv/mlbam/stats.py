"""

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

# TEAM_CODE_ID_MAP = {'ari':, 'atl':, 'bal':, 'bos':, 'chc':, 'cws':, 'cin':, 'cle':,
#                     'col':, 'det':, 'fla':, 'hou':, 'kan':, 'laa':, 'lad':, 'mil':,
#                     'min':, 'nym':, 'nyy':, 'oak':, 'phi':, 'pit':, 'sd':, 'sf':, 
#                     'sea':, 'stl':, 'tb':, 'tex':, 'tor':, 'wsh':}

TEAMS_URL = 'http://statsapi.mlb.com/api/v1/teams?season={season}&leagueIds=103,104'

# http://statsapi-default-elb-prod-876255662.us-east-1.elb.amazonaws.com/docs/

# STATS_GROUPS=('hitting', 'fielding', 'pitching')
# STATS_TYPES=('career', 'season')j
PERSON_STATS_URL = 'http://statsapi.mlb.com/api/v1/people/{personId}?hydrate=stats(group={statsgroup},type={statstype})'
# http://statsapi.mlb.com/api/v1/people/545361?hydrate=stats(group=[hitting,fielding,pitching],type=season)
# http://statsapi.mlb.com/api/v1/people/{personId}?hydrate=stats(group=[hitting,fielding],type=season)

MULTI_PERSON_STATS_URL = 'http://statsapi.mlb.com/api/v1/people?personIds={personIds},&hydrate=stats(group=[hitting,fielding,pitching],type=season,season={season})'
# http://statsapi.mlb.com/api/v1/people?personIds=545361,592273,&hydrate=stats(group=[hitting,fielding,pitching],type=season,season=2019)
# http://statsapi.mlb.com/api/v1/people?personIds=545361,592273,571704&hydrate=stats(group=[hitting,fielding,pitching],type=season,season=2018)

# season=2019 season=datetime.now().year
# see http://statsapi.mlb.com/api/v1/rosterTypes
# 
ROSTER_TYPES = { 'active': 'active', 'full': 'fullSeason', '40man': '40man' }
#ROSTER_URL = 'http://statsapi.mlb.com/api/v1/teams/{teamId}/roster?rosterType=active&season={season}'
ROSTER_URL = 'http://statsapi.mlb.com/api/v1/teams/{teamId}/roster?rosterType={rosterType}&season={season}'
#ROSTER_URL = 'http://statsapi.mlb.com/api/v1/teams/{teamId}/roster?rosterType=40man&season={season}'
# Blue Jays: http://statsapi.mlb.com/api/v1/teams/141/roster?rosterType=active&season=2019

# http://statsapi.mlb.com/api/v1/statTypes
STAT_TYPES = ('pecota', 'pecotaRos', 'yearByYear', 'yearByYearAdvanced', 'season', 'seasonAdvanced',
              'career', 'careerStatSplits', 'gameLog', 'playLog', 'pitchLog', 'metricLog', 'metricAverages',
              'pitchArsenal', 'outsAboveAverage', 'expectedStatistics', 'catcherFraming', 'sprayChart',
              'vsPlayer', 'vsPlayerTotal', 'vsPlayer5Y', 'vsTeam', 'vsTeam5Y', 'vsTeamTotal',
              'lastXGames', 'byDateRange', 'byMonth', 'byDayOfWeek',
              'rankings', 'rankingsByYear', 'hotColdZones', 'availableStats',
              'opponentsFaced', 'statSplits', 'atGameStart', 'vsOpponents')

# http://statsapi.mlb.com/api/v1/statGroups
STAT_GROUPS = ('hitting', 'pitching', 'fielding', 'catching', 'running', 'game', 'team', 'streak')

# http://statsapi.mlb.com/api/v1/stats?group=hitting&stats=season&teamId=141
# http://statsapi.mlb.com/api/v1/teams/141/stats?season=2019&stats=season&group=hitting


HITTING_STATS_ALL = (('gamesPlayed', 'GP', '{:>4}'), ('atBats', 'AB', '{:>4}'), ('hits', 'H', '{:>4}'),
                     ('rbi', 'RBI', '{:>4}'), ('runs', 'R', '{:>4}'), ('doubles', 'DB', '{:>4}'),
                     ('triples', 'TR', '{:>4}'), ('homeRuns', 'HR', '{:>4}'), ('strikeOuts', 'SO', '{:>4}'),
                     ('baseOnBalls', 'BB', '{:>4}'), ('stolenBases', 'SB', '{:>4}'),
                     ('avg', 'AVG', '{:>5}'), ('obp', 'OBP', '{:>5}'), ('ops', 'OPS', '{:>5}'),
                     ('slg', 'SLG', '{:>5}'), ('babip', 'BABIP', '{:>5}'))
# some simple lists based on above
HITTING_STATS_JSON = [x[0] for x in HITTING_STATS_ALL]
HITTING_STATS_HEADINGS = [x[1] for x in HITTING_STATS_ALL]
HITTING_STATS_FMTS = [x[2] for x in HITTING_STATS_ALL]

FIELDING_STATS_ALL = (('games', 'GP', '{:>4}'), ('gamesStarted', 'GS', '{:>4}'), ('assists', 'A', '{:>4}'),
                      ('putOuts', 'PO', '{:>4}'), ('errors', 'ERR', '{:>4}'),
                      ('chances', 'CH', '{:>5}'), ('fielding', 'F%', '{:>6}'))
FIELDING_STATS_JSON = [x[0] for x in FIELDING_STATS_ALL]
FIELDING_STATS_HEADINGS = [x[1] for x in FIELDING_STATS_ALL]
FIELDING_STATS_FMTS = [x[2] for x in FIELDING_STATS_ALL]

PITCHING_STATS_ALL = (('gamesPlayed', 'GP', '{:>4}'), ('gamesStarted', 'GS', '{:>4}'), ('inningsPitched', 'IP', '{:>5}'),
                      ('wins', 'W', '{:>3}'), ('losses', 'L', '{:>3}'), ('saves', 'S', '{:>3}'),
                      ('runs', 'R', '{:>4}'), ('hits', 'H', '{:>4}'), ('homeRuns', 'HR', '{:>4}'),
                      ('strikeOuts', 'SO', '{:>4}'), ('baseOnBalls', 'BB', '{:>4}'), ('earnedRuns', 'ER', '{:>4}'),
                      ('era', 'ERA', '{:>5}'), ('avg', 'AVG', '{:>5}'), ('whip', 'WHIP', '{:>5}'))
PITCHING_STATS_JSON = [x[0] for x in PITCHING_STATS_ALL]
PITCHING_STATS_HEADINGS = [x[1] for x in PITCHING_STATS_ALL]
PITCHING_STATS_FMTS = [x[2] for x in PITCHING_STATS_ALL]

# Get teams:
# http://statsapi.mlb.com/api/v1/teams?season=2019&leagueIds=103,104

"""
stats=team, filter by -o
stats=leaders, filter by league

"""

def _match(input_option, full_option):
    num_chars = len(input_option)
    return input_option[:num_chars] == full_option[:num_chars]


def _get_roster(team_id, roster_type, season):
    json_data = util.request_json(ROSTER_URL.format(teamId=team_id, rosterType=roster_type, season=season), 'roster-{}'.format(team_id))
    roster = dict()
    for person in json_data['roster']:
        person_id = str(person['person']['id'])
        roster[person_id] = dict()
        roster[person_id]['fullName'] = person['person']['fullName']
        roster[person_id]['link'] = person['person']['link']
        roster[person_id]['jerseyNumber'] = person['jerseyNumber']
        roster[person_id]['position'] = person['position']['abbreviation']
        roster[person_id]['status'] = person['status']['code']
    return roster


def get_teamcode_to_id_dict(season):
    json_data = util.request_json(TEAMS_URL.format(season=season), 'teams')
    team_code_id_map = dict()
    for team in json_data['teams']:
        team_code_id_map[team['abbreviation'].lower()] = team['id']
    # print(str(team_code_id_map))
    return team_code_id_map


def _get_person_stats(person_ids, season):
    json_data = util.request_json(MULTI_PERSON_STATS_URL.format(personIds=person_ids, season=season), 'person-stats')
    return json_data


def get_stats(target, date_str=None, team_code_id_map=None):
    """Displays team stats

    stats=team, filter by -o
    stats=leaders, filter by league

    For team:
    - get roster
    - get list of playerIds
    - get stats for playerIds

    """
    LOG.debug('Getting stats for %s, %s', target, date_str)
    # if date_str == time.strftime("%Y-%m-%d"):
    #     # strip out date string from url (issue #5)
    #     date_str = None

    if not target:
        LOG.error('no target given')
        return False

    category = 'all'
    roster_type = 'active'
    split_target = target.split(':')
    if target.startswith('league'):
        LOG.error('Not implemented yet.')
        return False
    if target.startswith('rookie'):
        LOG.error('Not implemented yet.')
        return False
    else:
        team_code = target.split(':')[0]
        if len(split_target) > 1:
            category = target.split(':')[1]
            if category == '':
                category = 'all'
        if len(split_target) > 2:
            roster_type = target.split(':')[2]
            if roster_type not in ROSTER_TYPES:
                LOG.error('Invalid roster type: %s', roster_type)
                return False
            roster_type = ROSTER_TYPES[roster_type]

    if not date_str:
        date_str = datetime.strftime(datetime.today(), "%Y-%m-%d")

    season = date_str.split('-')[0]
    if not team_code_id_map:
        team_code_id_map = get_teamcode_to_id_dict(season)

    team_id = team_code_id_map[team_code]

    roster = _get_roster(team_id, roster_type, season)
    person_ids = ','.join(list(roster))

    # Data
    person_stats_json = _get_person_stats(person_ids, season)
    stats = dict()
    for person_stats in person_stats_json['people']:
        # key: personId
        player_name = person_stats['lastInitName']
        stats[player_name] = dict()
        stats[player_name]['name'] = player_name
        stats[player_name]['player_id'] = person_stats['id']
        stats[player_name]['position'] = person_stats['primaryPosition']['abbreviation']
        if 'stats' not in person_stats:
            continue

        # Pull out stats based on hitting, fielding, pitching
        # They are put into the stats dictionary.
        for person_stat in person_stats['stats']:

            stats_type = person_stat['group']['displayName']

            if stats_type == 'hitting' and category in ('all', 'hitting'):
                for splits in person_stat['splits']:
                    if 'team' in splits and splits['team']['id'] == team_id:
                        split_stats = splits['stat']
                        if split_stats['atBats'] > 0:
                            stats[player_name]['hitting'] = dict()
                            for stat_name in HITTING_STATS_JSON:
                                stats[player_name]['hitting'][stat_name] = str(split_stats[stat_name])

            elif stats_type == 'fielding' and category in ('all', 'fielding'):
                # note: the splits are per-position
                stats[player_name]['fielding'] = dict()
                for splits in person_stat['splits']:
                    if 'team' in splits and splits['team']['id'] == team_id:
                        position = splits['stat']['position']['abbreviation']
                        stats[player_name]['fielding'][position] = dict()
                        for stat_name in FIELDING_STATS_JSON:
                            stats[player_name]['fielding'][position][stat_name] = str(splits['stat'][stat_name])

            elif stats_type == 'pitching' and category in ('all', 'pitching'):
                stats[player_name]['pitching'] = dict()
                for splits in person_stat['splits']:
                    if 'team' in splits and splits['team']['id'] == team_id:
                        for stat_name in PITCHING_STATS_JSON:
                            stats[player_name]['pitching'][stat_name] = str(splits['stat'][stat_name])

    # Presentation
    color_on = ''
    color_off = ''

    outl = list()

    if category in ('all', 'hitting'):
        outl.append('HITTING')
        hitting_stats_fmt = ' '.join(HITTING_STATS_FMTS)
        hitting_stats_hdr = hitting_stats_fmt.format(*[hdr for hdr in HITTING_STATS_HEADINGS])
        hitting_fmt = '{coloron}{name:<26}{hitting_stats}{coloroff}'
        outl.append(hitting_fmt.format(coloron=color_on, coloroff=color_off, name='-------', hitting_stats=hitting_stats_hdr))
        for player_name in sorted(list(stats)):
            if 'hitting' in stats[player_name] and stats[player_name]['position'] != 'P':
                hitting_stats = hitting_stats_fmt.format(*[stats[player_name]['hitting'][statval] for statval in HITTING_STATS_JSON])
                outl.append(hitting_fmt.format(coloron=color_on, coloroff=color_off,
                                               name=player_name, hitting_stats=hitting_stats))
        outl.append('')
        outl.append(hitting_fmt.format(coloron=color_on, coloroff=color_off, name='Pitchers:', hitting_stats=hitting_stats_hdr))
        for player_name in sorted(list(stats)):
            if 'hitting' in stats[player_name] and stats[player_name]['position'] == 'P':
                hitting_stats = hitting_stats_fmt.format(*[stats[player_name]['hitting'][statval] for statval in HITTING_STATS_JSON])
                outl.append(hitting_fmt.format(coloron=color_on, coloroff=color_off,
                                               name=player_name, hitting_stats=hitting_stats))
        if category in 'all':
            outl.append('')

    if category in ('all', 'fielding'):
        outl.append('FIELDING')
        fielding_stats_fmt = ' '.join(FIELDING_STATS_FMTS)
        fielding_stats_hdr = fielding_stats_fmt.format(*[hdr for hdr in FIELDING_STATS_HEADINGS])
        fielding_fmt = '{coloron}{name:<26}{pos:>3}{fielding_stats}{coloroff}'
        outl.append(fielding_fmt.format(coloron=color_on, coloroff=color_off, name='--------', pos='POS', fielding_stats=fielding_stats_hdr))
        for player_name in sorted(list(stats)):
            player_name_disp = player_name
            if 'fielding' in stats[player_name] and stats[player_name]['position'] != 'P':
                iter_count = 0
                for position in stats[player_name]['fielding']:
                    iter_count += 1
                    fielding_stats = fielding_stats_fmt.format(*[stats[player_name]['fielding'][position][statval] for statval in FIELDING_STATS_JSON])
                    if len(stats[player_name]['fielding']) > 1 and iter_count > 1:
                        player_name_disp = ' -'
                    outl.append(fielding_fmt.format(coloron=color_on, coloroff=color_off,
                                                    name=player_name_disp, pos=position, fielding_stats=fielding_stats))
        outl.append('')
        outl.append(fielding_fmt.format(coloron=color_on, coloroff=color_off, name='PITCHERS:', pos='POS', fielding_stats=fielding_stats_hdr))
        for player_name in sorted(list(stats)):
            player_name_disp = player_name
            if 'fielding' in stats[player_name] and stats[player_name]['position'] == 'P':
                iter_count = 0
                for position in stats[player_name]['fielding']:
                    iter_count += 1
                    fielding_stats = fielding_stats_fmt.format(
                        *[stats[player_name]['fielding'][position][statval] for statval in FIELDING_STATS_JSON])
                    if len(stats[player_name]['fielding']) > 1 and iter_count > 1:
                        player_name_disp = ''
                    outl.append(fielding_fmt.format(coloron=color_on, coloroff=color_off,
                                                    name=player_name_disp, pos=position, fielding_stats=fielding_stats))
        if category in 'all':
            outl.append('')

    if category in ('all', 'pitching'):
        outl.append('PITCHING')
        outl.append('--------')
        pitching_stats_fmt = ' '.join(PITCHING_STATS_FMTS)
        pitching_stats_hdr = pitching_stats_fmt.format(*[hdr for hdr in PITCHING_STATS_HEADINGS])
        pitching_fmt = '{coloron}{name:<26}{pitching_stats}{coloroff}'
        # outl.append(pitching_fmt.format(coloron=color_on, coloroff=color_off, name='--------', pitching_stats=pitching_stats_hdr))
        # outl.append('----- Starting -----')
        # outl.append('STARTING')
        outl.append(pitching_fmt.format(coloron=color_on, coloroff=color_off, name='STARTING:', pitching_stats=pitching_stats_hdr))
        for player_name in sorted(list(stats)):
            if 'pitching' in stats[player_name] and stats[player_name]['position'] == 'P' \
                    and int(stats[player_name]['pitching']['gamesStarted']) > 0:
                pitching_stats = pitching_stats_fmt.format(*[stats[player_name]['pitching'][statval] for statval in PITCHING_STATS_JSON])
                outl.append(pitching_fmt.format(coloron=color_on, coloroff=color_off,
                                                name=player_name, pitching_stats=pitching_stats))
        # outl.append('----- Relief -----')
        # outl.append('BULLPEN')
        outl.append('')
        outl.append(pitching_fmt.format(coloron=color_on, coloroff=color_off, name='BULLPEN:', pitching_stats=pitching_stats_hdr))
        for player_name in sorted(list(stats)):
            if 'pitching' in stats[player_name] and stats[player_name]['position'] == 'P' \
                    and int(stats[player_name]['pitching']['gamesStarted']) < 1:
                pitching_stats = pitching_stats_fmt.format(*[stats[player_name]['pitching'][statval] for statval in PITCHING_STATS_JSON])
                outl.append(pitching_fmt.format(coloron=color_on, coloroff=color_off,
                                                name=player_name, pitching_stats=pitching_stats))
        for player_name in sorted(list(stats)):
            if 'pitching' in stats[player_name] and stats[player_name]['position'] != 'P':
                pitching_stats = pitching_stats_fmt.format(*[stats[player_name]['pitching'][statval] for statval in PITCHING_STATS_JSON])
                outl.append(pitching_fmt.format(coloron=color_on, coloroff=color_off,
                                                name=player_name, pitching_stats=pitching_stats))

    print('\n'.join(outl))

    # if _match(stats_option, 'all') or _match(stats_option, 'hitting'):
    #     display_team_stats_hitting(date_str, args_filter, rank_tag='divisionRank', header_tags=('league', 'division'))
    #     if _match(stats_option, 'all'):
    #         print('')
    # if _match(stats_option, 'all') or _match(stats_option, 'wildcard'):
    #     _display_standings('wildCard', 'Wildcard', date_str, args_filter, rank_tag='wildCardRank', header_tags=('league', ))
    #     if _match(stats_option, 'all'):
    #         print('')
    # if _match(stats_option, 'all') or _match(stats_option, 'overall') \
    #         or _match(stats_option, 'league') or _match(stats_option, 'conference'):
    #     _display_standings('byLeague', 'League', date_str, args_filter, rank_tag='leagueRank', header_tags=('league', ))
    #     if _match(stats_option, 'all'):
    #         print('')

    # if _match(stats_option, 'playoff') or _match(stats_option, 'postseason'):
    #     _display_standings('postseason', 'Playoffs', date_str, args_filter)
    # if _match(stats_option, 'preseason'):
    #     _display_standings('preseason', 'Preseason', date_str, args_filter)


