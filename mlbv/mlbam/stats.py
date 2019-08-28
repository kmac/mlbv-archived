"""

"""

import logging

from datetime import datetime

import mlbv.mlbam.mlbapidata as mlbapidata
import mlbv.mlbam.common.displayutil as displayutil
import mlbv.mlbam.common.config as config
import mlbv.mlbam.common.request as request
import mlbv.mlbam.common.util as util

from mlbv.mlbam.common.displayutil import ANSI


LOG = logging.getLogger(__name__)

DEFAULT_LEAGUE_STATS_LIMIT = 10

# http://statsapi-default-elb-prod-876255662.us-east-1.elb.amazonaws.com/docs/

# STATS_GROUPS=('hitting', 'fielding', 'pitching')
# STATS_TYPES=('career', 'season')j
PERSON_STATS_URL = 'http://statsapi.mlb.com/api/v1/people/{personId}?hydrate=stats(group={statsgroup},type={statstype})'
# http://statsapi.mlb.com/api/v1/people/545361?hydrate=stats(group=[hitting,fielding,pitching],type=season)
# http://statsapi.mlb.com/api/v1/people/{personId}?hydrate=stats(group=[hitting,fielding],type=season)

MULTI_PERSON_STATS_URL = ('http://statsapi.mlb.com/api/v1/people?personIds={personIds},'
                          '&hydrate=stats(group={groups},type=season,season={season})')
# http://statsapi.mlb.com/api/v1/people?personIds=545361,592273,&hydrate=stats(group=[hitting,fielding,pitching],type=season,season=2019)
# http://statsapi.mlb.com/api/v1/people?personIds=545361,592273,571704&hydrate=stats(group=[hitting,fielding,pitching],type=season,season=2018)

# see http://statsapi.mlb.com/api/v1/rosterTypes
ROSTER_TYPES = {'active': 'active', 'full': 'fullSeason', '40man': '40man'}
ROSTER_URL = 'http://statsapi.mlb.com/api/v1/teams/{teamId}/roster?rosterType={rosterType}&season={season}'
# Blue Jays: http://statsapi.mlb.com/api/v1/teams/141/roster?rosterType=active&season=2019

# http://statsapi.mlb.com/api/v1/statTypes
STAT_TYPES = ('pecota', 'pecotaRos', 'yearByYear', 'yearByYearAdvanced', 'season', 'seasonAdvanced',
              'career', 'careerStatSplits', 'gameLog', 'playLog', 'pitchLog', 'metricLog', 'metricAverages',
              'pitchArsenal', 'outsAboveAverage', 'expectedStatistics', 'catcherFraming', 'sprayChart',
              'vsPlayer', 'vsPlayerTotal', 'vsPlayer5Y', 'vsTeam', 'vsTeam5Y', 'vsTeamTotal',
              'lastXGames', 'byDateRange', 'byMonth', 'byDayOfWeek',
              'rankings', 'rankingsByYear', 'hotColdZones', 'availableStats',
              'opponentsFaced', 'statSplits', 'atGameStart', 'vsOpponents')

# http://statsapi.mlb.com/api/v1/leagueLeaderTypes

# http://statsapi.mlb.com/api/v1/statGroups
STAT_GROUPS = ('hitting', 'pitching', 'fielding', 'catching', 'running', 'game', 'team', 'streak')

# http://statsapi.mlb.com/api/v1/stats?group=hitting&stats=season&teamId=141
# http://statsapi.mlb.com/api/v1/teams/141/stats?season=2019&stats=season&group=hitting


HITTING_STATS = (('gamesPlayed', 'GP', '{:>4}'), ('atBats', 'AB', '{:>4}'), ('hits', 'H', '{:>4}'),
                 ('rbi', 'RBI', '{:>4}'), ('runs', 'R', '{:>4}'), ('doubles', 'DB', '{:>4}'),
                 ('triples', 'TR', '{:>4}'), ('homeRuns', 'HR', '{:>4}'), ('strikeOuts', 'SO', '{:>4}'),
                 ('baseOnBalls', 'BB', '{:>4}'), ('stolenBases', 'SB', '{:>4}'),
                 ('avg', 'AVG', '{:>5}'), ('obp', 'OBP', '{:>5}'), ('ops', 'OPS', '{:>5}'),
                 ('slg', 'SLG', '{:>5}'), ('babip', 'BABIP', '{:>5}'))
# some simple lists based on above
HITTING_STATS_JSON = [x[0] for x in HITTING_STATS]
HITTING_STATS_HEADINGS = [x[1] for x in HITTING_STATS]
HITTING_STATS_FMTS = [x[2] for x in HITTING_STATS]

FIELDING_STATS = (('games', 'GP', '{:>4}'), ('gamesStarted', 'GS', '{:>4}'), ('assists', 'A', '{:>4}'),
                  ('putOuts', 'PO', '{:>4}'), ('errors', 'ERR', '{:>4}'),
                  ('chances', 'CH', '{:>5}'), ('fielding', 'F%', '{:>6}'))
FIELDING_STATS_JSON = [x[0] for x in FIELDING_STATS]
FIELDING_STATS_HEADINGS = [x[1] for x in FIELDING_STATS]
FIELDING_STATS_FMTS = [x[2] for x in FIELDING_STATS]

PITCHING_STATS = (('gamesPlayed', 'GP', '{:>4}'), ('gamesStarted', 'GS', '{:>4}'), ('inningsPitched', 'IP', '{:>5}'),
                  ('wins', 'W', '{:>3}'), ('losses', 'L', '{:>3}'), ('saves', 'S', '{:>3}'),
                  ('runs', 'R', '{:>4}'), ('hits', 'H', '{:>4}'), ('homeRuns', 'HR', '{:>4}'),
                  ('strikeOuts', 'SO', '{:>4}'), ('baseOnBalls', 'BB', '{:>4}'), ('earnedRuns', 'ER', '{:>4}'),
                  ('era', 'ERA', '{:>5}'), ('avg', 'AVG', '{:>5}'), ('whip', 'WHIP', '{:>5}'))
PITCHING_STATS_JSON = [x[0] for x in PITCHING_STATS]
PITCHING_STATS_HEADINGS = [x[1] for x in PITCHING_STATS]
PITCHING_STATS_FMTS = [x[2] for x in PITCHING_STATS]


LEAGUE_LEADER_TYPES_URL = 'http://statsapi.mlb.com/api/v1/leagueLeaderTypes'
LEAGUE_LEADER_TYPES_URL = ('http://statsapi.mlb.com/api/v1/stats/leaders?leaderCategories={leaderCategories}'
                           '&season={season}&sportId=1{leagueIdOptional}&statGroup={statGroup}&playerPool={playerPool}'
                           '&limit={limit}&fields=leagueLeaders,leaders,rank,value,team,name,league,name,person,fullName')

# statGroup=pitching, hitting, fielding, ...
# Available playerPool values: ['all','qualified','rookies'] (default is qualified)
LEAGUE_PLAYER_POOL_TYPES = ('all', 'qualified', 'rookies')

# http://statsapi.mlb.com/api/v1/stats/leaders?leaderCategories=homeRuns&season=2019&sportId=1&leagueId=103&statGroup=hitting&playerPool=qualified&limit=10
# http://statsapi.mlb.com/api/v1/stats/leaders?leaderCategories=homeRuns&season=2019&sportId=1&leagueId=103&statGroup=hitting&playerPool=qualified&limit=10&fields=leagueLeaders,leaders,rank,value,team,name,league,name,person,fullName


LEAGUE_STATS = {
    'hitting': (
        ('battingAverage', 'Average', 'AVG'),
        ('homeRuns', 'Home Runs', 'HR'),
        ('runsBattedIn', 'Runs Batted In', 'RBI'),
        ('hits', 'Hits', 'H'),
        ('runs', 'Runs', 'R'),
        ('onBasePlusSlugging', 'On-Base Plus Slugging', 'OPS'),
        ('onBasePercentage', 'On-Base Percentage', 'OBP'),
        ('sluggingPercentage', 'Slugging Percentage', 'SLG'),
        ('strikeouts', 'Strike Outs', 'K'),
        ('walks', 'Walks', 'BB'),
        ('stolenBases', 'Stolen Bases', 'SB'),
        # ('flyouts', 'Flyouts', 'FLY'),
        ('extraBaseHits', 'Extra Base Hits', 'EBH'),
        ('doubles', 'Doubles', 'DB'),
        ('triples', 'Triples', 'TR'),
        ('atBats', 'At Bats', 'AB'),
        ('groundIntoDoublePlays', 'Ground Into Double Plays', 'GIDP'),
    ),
    'fielding': (
        ('errors', 'Errors', 'E'),
        ('throwingErrors', 'Throwing Errors', 'TE'),
        ('assists', 'Assists', 'A'),
        # Boring: too many at 100%: ('fieldingPercentage', 'Fielding Percentage', 'FP'),
        ('doublePlays', 'Double Plays', 'DP'),
        # ('outfieldAssists', 'Outfield Assists', 'OA'),
        ('putOuts', 'Putouts', 'PO'),
        ('rangeFactorPerGame', 'Range Factor Per Game', 'RF/G'),
        ('rangeFactorPer9Inn', 'Range Factor Per 9 Innings', 'RF/9'),
    ),
    'pitching': (
        ('earnedRunAverage', 'Earned Run Average', 'ERA'),
        ('walksAndHitsPerInningPitched', 'Walks & Hits / Inning Pitched', 'WHIP'),
        ('strikeouts', 'Strikeouts', 'K'),
        ('walks', 'Walks', 'BB'),
        ('wins', 'Wins', 'W'),
        ('winPercentage', 'Win Percentage', 'W%'),
        ('losses', 'Losses', 'L'),
        ('saves', 'Saves', 'SV'),
        ('holds', 'Holds', 'HOLD'),
        ('hitsPer9Inn', 'Hits Per 9 Innings', 'H/9'),
        ('strikeoutsPer9Inn', 'Strikeouts Per 9 Innings', 'K/9'),
        ('walksPer9Inn', 'Walks Per 9 Innings', 'BB/9'),
        ('strikeoutWalkRatio', 'Strikeout/Walk Ratio', 'K/BB'),
        ('wildPitch', 'Wild Pitch', 'WP'),
        ('hitBatsman', 'Hit Batsman', 'HB'),
        # ('gamesPlayed', 'Games Played', 'GP'),
        ('inningsPitched', 'Innings Pitched', 'IP'),
        ('totalBattersFaced', 'Total Batters Faced', 'TBat'),
        ('numberOfPitches', 'Number of Pitches', 'NumP'),
        ('pitchesPerInning', 'Pitches Per Inning', 'P/I'),
        # ('gamesStarted', 'Games Started', 'GS'),
        # ('shutouts', 'Shutouts', 'SO'),
        # ('passedBalls', 'Passed Balls', 'PB'),
        # ('airOuts', 'Air Outs', 'AO'),
        # ('balk', 'Balk', 'BALK'),
        # ('blownSaves', 'Blown Saves', 'BSV'),
        # ('chances', 'Chances', 'CH'),
        # ('completeGames', 'Complete Games', 'CG'),
        # ('earnedRun', 'Earned Run', 'ER'),
        # ('innings', 'Innings', 'I'),
        # ('pickoffs', 'Pickoffs', 'PICK'),
        # ('saveOpportunities', 'Save Opportunities', 'SvO'),
    )
}


def _get_roster(team_id, roster_type, season):
    json_data = request.request_json(ROSTER_URL.format(teamId=team_id, rosterType=roster_type, season=season),
                                     'roster-{}-{}-{}'.format(team_id, roster_type, season),
                                     cache_stale=request.CACHE_DAY)
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


def _get_person_stats(person_ids, category, roster_type, season):
    if category == 'all':
        groups = '[hitting,fielding,pitching]'
    else:
        groups = category
    json_data = request.request_json(MULTI_PERSON_STATS_URL.format(personIds=person_ids, groups=groups, season=season),
                                     'person-stats-{}-{}-{}-{}'.format(groups, roster_type, season, str(person_ids)),
                                     request.CACHE_SHORT)
    return json_data


def _parse_stats_target(stats_target):
    category = 'all'
    qualifier = None
    split_target = stats_target.split(':')
    target = split_target[0]
    if len(split_target) > 1 and split_target[1]:
        category = split_target[1]
        if category == 'batting':
            category = 'hitting'
    if len(split_target) > 2 and split_target[2]:
        qualifier = split_target[2]
    return target, category, qualifier


def get_stats(target_input, date_str=None, args_filter=None):
    """Displays team stats

    stats=team, filter by -o
    stats=leaders, filter by league

    For team:
    - get roster
    - get list of playerIds
    - get stats for playerIds

    """
    LOG.debug('Getting stats for %s, %s', target_input, date_str)

    if not target_input:
        LOG.error('no target given')
        return False

    if not date_str:
        date_str = datetime.strftime(datetime.today(), "%Y-%m-%d")

    season = date_str.split('-')[0]

    # strip out common mis-use of prepending team: to the team abbrev:
    if target_input.startswith('team:'):
        target_input = target_input[len('team:'):]

    target, category, qualifier = _parse_stats_target(target_input)

    if target == 'league':
        limit = config.CONFIG.parser.get('stats_limit', DEFAULT_LEAGUE_STATS_LIMIT)
        handle_league_stats(category, qualifier, season, limit, args_filter)
    else:
        # fall-through: must be given a team abbrev:
        team_abbrev = target
        handle_team_stats(team_abbrev, category, qualifier, season)


def handle_league_stats(category, qualifier, season, limit, args_filter):
    """Handler for gather/display overal league stats.

    League Format:  league:[category]:[qualifier]
        [category]: one of: hitting, fielding, pitching, all [default: all]
        [qualifier]: all, qualified, rookies [default: qualified]

    Examples: league:hitting:qualified
              league:hitting:rookies
              league:hitting:all
              league:pitching
    """
    if util.substring_match(category, 'all'):
        categories = ['hitting', 'fielding', 'pitching']
    elif util.substring_match(category, 'hitting'):
        categories = ['hitting', ]
    elif util.substring_match(category, 'fielding'):
        categories = ['fielding', ]
    elif util.substring_match(category, 'pitching'):
        categories = ['pitching', ]
    else:
        LOG.error('Invalid category: %s', category)
        return

    if not qualifier:
        qualifier = 'qualified'
    else:
        expanded_qualifier = util.expand_substring_match(qualifier, LEAGUE_PLAYER_POOL_TYPES)
        if not expanded_qualifier:
            LOG.error('Invalid qualifier: %s', qualifier)
            return
        qualifier = expanded_qualifier

    league_id = ''
    if args_filter and args_filter in mlbapidata.LEAGUE_FILTERS:
        league_id = mlbapidata.LEAGUE_ID_MAP[args_filter]

    for catg in categories:
        stats = _get_league_stats(catg, qualifier, season, league_id, limit)
        _display_league_stats(stats, catg, season, limit)


def _get_league_stats(category, qualifier, season, league_id, limit):
    stats = dict()
    player_pool = qualifier
    for leader_category, title, heading in LEAGUE_STATS[category]:
        stats[leader_category] = list()
        if league_id:
            league_id_optional = '&leagueId={}'.format(league_id)
            league_stats = 'leaguestats-{}-{}-{}-{}-{}'.format(category, leader_category, qualifier, season, league_id)
        else:
            league_id_optional = ''
            league_stats = 'leaguestats-{}-{}-{}-{}'.format(category, leader_category, qualifier, season)
        json_data = request.request_json(LEAGUE_LEADER_TYPES_URL.format(leaderCategories=leader_category, season=season,
                                                                        leagueIdOptional=league_id_optional, statGroup=category,
                                                                        playerPool=player_pool, limit=limit),
                                         league_stats, request.CACHE_SHORT)
        # Fill out/normalize the stats for each leader. This format is common across all the leader stats
        for league_leaders in json_data['leagueLeaders']:
            if 'leaders' not in league_leaders:
                continue
            for leader_info in league_leaders['leaders']:
                entry = {'rank': '', 'value': '', 'team': '', 'league': '', 'name': ''}
                if 'rank' in leader_info:
                    entry['rank'] = leader_info['rank']
                if 'value' in leader_info:
                    entry['value'] = leader_info['value']
                if 'team' in leader_info:
                    entry['team'] = leader_info['team']['name']
                if 'league' in leader_info:
                    entry['league'] = leader_info['league']['name']
                if 'person' in leader_info:
                    entry['name'] = leader_info['person']['fullName']
                stats[leader_category].append(entry)
    return stats


def _display_league_stats(stats, category, season, limit):
    outl = list()
    # color_on = '' # color_off = ''
    top_header = '{} - {}'.format(season, category.upper())
    outl.append(top_header)
    outl.append('-' * len(top_header))
    outl.append('')
    if int(limit) < 100:
        stats_fmt = '{rank:>2} {name:<30} {value:>6} {team:>26} {league:>4}'
    else:
        stats_fmt = '{rank:>3} {name:<30} {value:>6} {team:>26} {league:>4}'
    for leader_category, title, heading in LEAGUE_STATS[category]:
        if stats[leader_category]:
            # header:
            outl.append(stats_fmt.format(rank='', name=title.upper(), value=heading, team='TEAM', league='LG'))
            # individual stats:
            for stat in stats[leader_category]:
                outl.append(stats_fmt.format(rank=stat['rank'], name=stat['name'], value=stat['value'],
                                             team=stat['team'], league=stat['league']))
            outl.append('')
    print('\n'.join(outl))


def handle_team_stats(team_abbrev, category, roster_type, season):
    """Fetches and displays team stats.

    Team Format:  <team>:[category]:[qualifier]
        <team>: the team abbreviation
        [category]: one of: hitting, fielding, pitching, all [default: all]
        [qualifier]: the roster type: active, full, 40man

    Examples: tor:hitting:active  # active roster only (default)
              tor:hitting:full    # full season roster
              tor:hitting:40man   # 40-man roster
              tor:pitching
              tor:fielding
    """

    if not roster_type:
        roster_type = 'active'
    else:
        found = False
        for rtype in ROSTER_TYPES:
            if util.substring_match(roster_type, rtype):
                found = True
                roster_type = rtype
                break
        if not found:
            LOG.error('Invalid roster type: %s', roster_type)
            return

    roster_type = ROSTER_TYPES[roster_type]

    if not category:
        category = 'all'

    team_id = mlbapidata.get_team_id(team_abbrev, season)

    roster = _get_roster(team_id, roster_type, season)
    person_ids = ','.join(list(roster))

    # Data
    person_stats_json = _get_person_stats(person_ids, category, roster_type, season)
    stats = _get_team_person_stats(person_stats_json, team_id, category)
    _display_team_stats(stats, category)


def _get_team_person_stats(person_stats_json, team_id, category):
    """Fetches team stats into a dictionary."""
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

            if stats_type == 'hitting' and (util.substring_match(category, 'all') or util.substring_match(category, 'hitting')):
                for splits in person_stat['splits']:
                    if 'team' in splits and splits['team']['id'] == team_id:
                        split_stats = splits['stat']
                        if split_stats['atBats'] > 0:
                            stats[player_name]['hitting'] = dict()
                            for stat_name in HITTING_STATS_JSON:
                                if stat_name in split_stats:
                                    stats[player_name]['hitting'][stat_name] = str(split_stats[stat_name])
                                else:
                                    stats[player_name]['hitting'][stat_name] = '-'

            elif stats_type == 'fielding' and (util.substring_match(category, 'all') or util.substring_match(category, 'fielding')):
                # note: the splits are per-position
                stats[player_name]['fielding'] = dict()
                for splits in person_stat['splits']:
                    if 'team' in splits and splits['team']['id'] == team_id:
                        position = splits['stat']['position']['abbreviation']
                        stats[player_name]['fielding'][position] = dict()
                        for stat_name in FIELDING_STATS_JSON:
                            if stat_name in splits['stat']:
                                stats[player_name]['fielding'][position][stat_name] = str(splits['stat'][stat_name])
                            else:
                                stats[player_name]['fielding'][position][stat_name] = '-'

            elif stats_type == 'pitching' and (util.substring_match(category, 'all') or util.substring_match(category, 'pitching')):
                stats[player_name]['pitching'] = dict()
                for splits in person_stat['splits']:
                    if 'team' in splits and splits['team']['id'] == team_id:
                        for stat_name in PITCHING_STATS_JSON:
                            if stat_name in splits['stat']:
                                stats[player_name]['pitching'][stat_name] = str(splits['stat'][stat_name])
                            else:
                                stats[player_name]['pitching'][stat_name] = '-'
    return stats


def _display_team_stats(stats, category):
    """Presentation of team stats."""
    color_on = ''
    color_off = ''

    outl = list()

    if util.substring_match(category, 'all') or util.substring_match(category, 'hitting'):
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
        if category == 'all':
            outl.append('')

    if util.substring_match(category, 'all') or util.substring_match(category, 'fielding'):
        outl.append('FIELDING')
        fielding_stats_fmt = ' '.join(FIELDING_STATS_FMTS)
        fielding_stats_hdr = fielding_stats_fmt.format(*[hdr for hdr in FIELDING_STATS_HEADINGS])
        fielding_fmt = '{coloron}{name:<26}{pos:>3}{fielding_stats}{coloroff}'
        outl.append(fielding_fmt.format(coloron=color_on, coloroff=color_off,
                                        name='--------', pos='POS', fielding_stats=fielding_stats_hdr))
        for player_name in sorted(list(stats)):
            player_name_disp = player_name
            if 'fielding' in stats[player_name] and stats[player_name]['position'] != 'P':
                iter_count = 0
                for position in stats[player_name]['fielding']:
                    iter_count += 1
                    fielding_stats = fielding_stats_fmt.format(*[stats[player_name]['fielding'][position][statval]
                                                                 for statval in FIELDING_STATS_JSON])
                    if len(stats[player_name]['fielding']) > 1 and iter_count > 1:
                        player_name_disp = ' -'
                    outl.append(fielding_fmt.format(coloron=color_on, coloroff=color_off,
                                                    name=player_name_disp, pos=position, fielding_stats=fielding_stats))
        outl.append('')
        outl.append(fielding_fmt.format(coloron=color_on, coloroff=color_off,
                                        name='PITCHERS:', pos='POS', fielding_stats=fielding_stats_hdr))
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
        if category == 'all':
            outl.append('')

    if util.substring_match(category, 'all') or util.substring_match(category, 'pitching'):
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
            if 'pitching' in stats[player_name] and stats[player_name]['position'] != 'P' and stats[player_name]['pitching']:
                pitching_stats = pitching_stats_fmt.format(*[stats[player_name]['pitching'][statval] for statval in PITCHING_STATS_JSON])
                # pitching_stats = list()
                # # pitching_stats = pitching_stats_fmt.format(*[stats[player_name]['pitching'][statval]
                # for statval in PITCHING_STATS_JSON:
                #     if statval in stats[player_name]['pitching']:
                #         pitching_stats.append(stats[player_name]['pitching'][statval])
                #     else:
                #         print('player: {}, stats: {}'.format(player_name, stats[player_name]))
                #         pitching_stats.append('-')
                # pitching_stats = pitching_stats_fmt.format(pitching_stats)
                outl.append(pitching_fmt.format(coloron=color_on, coloroff=color_off,
                                                name=player_name, pitching_stats=pitching_stats))

    print('\n'.join(outl))
