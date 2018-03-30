"""
Models the game data retrieved via JSON.
"""
import logging

import mlbam.config as config


LOG = logging.getLogger(__name__)


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
