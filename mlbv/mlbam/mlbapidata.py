"""
Provides constants and functions to access basic data from the API.
"""

import logging

from datetime import datetime

import mlbv.mlbam.mlbconfig as mlbconfig

import mlbv.mlbam.common.displayutil as displayutil
import mlbv.mlbam.common.config as config
import mlbv.mlbam.common.request as request
import mlbv.mlbam.common.util as util

from mlbv.mlbam.common.displayutil import ANSI


LOG = logging.getLogger(__name__)


LEAGUE_ID_MAP = {
    'american': 103,
    'al': 103,
    'national': 104,
    'nl': 104,
}

TEAMS_URL = 'http://statsapi.mlb.com/api/v1/teams?season={season}&leagueIds=103,104'

TEAM_DICT = dict()  # indexed by season

LEAGUE_FILTERS = ('al', 'american', 'nl', 'national')
DIVISION_FILTERS = ('ale', 'alc', 'alw', 'nle', 'nlc', 'nlw')

FILTERS = {
    'favs': '',  # is filled out by config parser
    'ale': 'bal,bos,nyy,tb,tor',
    'alc': 'cle,cws,det,kc,min',
    'alw': 'hou,laa,oak,sea,tex',
    'nle': 'atl,mia,nym,phi,wsh',
    'nlc': 'chc,cin,mil,pit,stl,',
    'nlw': 'ari,col,lad,sd,sf',
}
FILTERS['al'] = '{},{},{}'.format(FILTERS['ale'], FILTERS['alc'], FILTERS['alw'])
FILTERS['nl'] = '{},{},{}'.format(FILTERS['nle'], FILTERS['nlc'], FILTERS['nlw'])



def get_team_dict(season):
    if not season:
        season = get_current_season()
    json_data = request.request_json(TEAMS_URL.format(season=season), 'teams-' + season, cache_stale=request.CACHE_DAY)
    global TEAM_DICT
    if season in TEAM_DICT:
        return TEAM_DICT[season]
    TEAM_DICT[season] = dict()
    for team in json_data['teams']:
        TEAM_DICT[season][team['id']] = {
            'name': team['name'],                          # San Diego Padres
            'abbreviation': team['abbreviation'].lower(),  # SD
            'teamName': team['teamName'],                  # Padres
            'teamCode': team['teamCode'],                  # sdn
            'fileCode': team['fileCode'],                  # sd
            'shortName': team['shortName'],                # San Diego
            'leagueId': team['league']['id'],
            'divisionId': team['division']['id'],
        }
    # print(str(TEAM_DICT))
    return TEAM_DICT[season]


def get_current_season():
    return datetime.strftime(datetime.today(), "%Y")


def get_team_abbrevs(season=None):
    if not season:
        season = get_current_season()
    team_dict = get_team_dict(season)
    team_abbrevs = [team_dict[team_id]['abbreviation'] for team_id in team_dict]
    # print(str(team_abbrevs))
    return team_abbrevs


def get_team_id(team_abbrev, season=None):
    team_dict = get_team_dict(season)
    for team_id in team_dict:
        if team_abbrev.lower() == team_dict[team_id]['abbreviation']:
            return team_id
    return None
    # raise Exception("Could not find team id for abbreviation '{}', season={}".format(team_abbrev, season))


def get_team_names_to_abbrevs_dict(season=None):
    team_dict = get_team_dict(season)
    # return [(team_dict[season][team_id]['name'], team_dict[season][team_id]['abbreviation']) for team_id in team_dict[season]]
    names_to_abbrevs = dict()
    for team_id in team_dict:
        names_to_abbrevs[team_dict[team_id]['name']] = team_dict[team_id]['abbreviation']
    return names_to_abbrevs


def get_team_abbrev(long_team_name, season=None):
    names_to_abbrevs = get_team_names_to_abbrevs_dict(season)
    return names_to_abbrevs[long_team_name]


def get_league_ids(args_filter=None):
    league_ids = '{},{}'.format(LEAGUE_ID_MAP['al'], LEAGUE_ID_MAP['nl'])
    if args_filter:
        if args_filter.startswith('al'):
            league_ids = LEAGUE_ID_MAP['al']
        elif args_filter.startswith('nl'):
            league_ids = LEAGUE_ID_MAP['nl']
    return league_ids


def is_fav(long_team_name):
    try:
        return get_team_abbrev(long_team_name) in util.get_csv_list(config.CONFIG.parser['favs'])
    except:
        LOG.exception("Unexpected exception")
        return False


def is_fav_by_id(team_id):
    for team_abbrev in util.get_csv_list(config.CONFIG.parser['favs']):
        if get_team_id(team_abbrev) == team_id:
            return True
    return False
