"""
Common gamedata utilities
"""

import logging

import mlbv.mlbam.common.config as config
import mlbv.mlbam.common.util as util


LOG = logging.getLogger(__name__)


def get_feedtype_keystring(feedtype_map):
    reverse_list = list()
    for longkey in feedtype_map:
        reverse_list.append('{}:{}'.format(feedtype_map[longkey], longkey))
    return ', '.join(reverse_list)


def convert_feedtype_to_short(feedtype, feedtype_map):
    if feedtype in feedtype_map:
        return feedtype_map[feedtype]
    return feedtype


def convert_to_long_feedtype(feed, feedtype_map):
    if feed in feedtype_map:
        return feed
    for feedtype in feedtype_map:
        if feedtype_map[feedtype] == feed:
            return feedtype
    return feed


def is_fav(game_rec):
    if 'favourite' in game_rec:
        return game_rec['favourite']
    if config.CONFIG.parser['favs'] is None or config.CONFIG.parser['favs'] == '':
        return False
    for fav in util.get_csv_list(config.CONFIG.parser['favs']):
        if fav in (game_rec['away']['abbrev'], game_rec['home']['abbrev']):
            return True
    return False


def apply_filter(game_rec, arg_filter, filters):
    """Returns the game_rec if the game matches the filter, or if no filtering is active.
    """
    if arg_filter == 'favs':
        arg_filter = config.CONFIG.parser['favs']
    elif arg_filter in filters:
        arg_filter = filters[arg_filter]
    elif not arg_filter:
        return game_rec

    # apply the filter
    for team in util.get_csv_list(arg_filter):
        if team in (game_rec['away']['abbrev'], game_rec['home']['abbrev']):
            return game_rec

    # no match
    return None
