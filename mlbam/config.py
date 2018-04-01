import configparser
import logging
import os
import sys


HIGHLIGHT_FEEDTYPES = ('condensed', 'recap')

# Note: 720p (best) is the 60fps stream
BANDWIDTH_CHOICES = ('worst', '360p', '540p', '720p_alt', '720p', 'best')

CONFIG = None  # holds a Config instance

# These are initialized/updated via the Config class
DEBUG = False
VERBOSE = False
VERIFY_SSL = True
SAVE_JSON_FILE_BY_TIMESTAMP = False  # normally false; will save many .json files if set
# SAVE_JSON_FILE_BY_TIMESTAMP = True  # normally false; will save many .json files if set

LOG = logging.getLogger(__name__)


class Config:
    """Contains the configuration data for use within the application, including a configparser instance
    for pulling in configuration from the 'config' file."""
    defaults = {  # is applied to initial config before reading from file - these are the defaults:
        'mlbv': {
            'username': '',
            'password': '',
            'favs': '',
            'fav_colour': 'cyan',
            'use_short_feeds': 'true',
            'filter': 'false',
            'cdn': 'akamai',
            'resolution': 'best',
            'video_player': 'mpv',
            'streamlink_highlights': 'true',  # if false will send url direct to video_player (no resolution selection)
            'streamlink_passthrough_highlights': 'true',  # allows seeking
            'streamlink_passthrough': 'false',
            'audio_player': 'mpv',
            'debug': 'false',
            'verbose': 'false',
            'game_critical_colour': 'yellow',
            'verify_ssl': 'true',
            'save_json_file_by_timestamp': 'false',
        }
    }
    platform = 'IPHONE'
    playback_scenario = 'HTTP_CLOUD_TABLET_60'
    ua_pc = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.97 Safari/537.36'
    ua_iphone = 'AppleCoreMedia/1.0.0.15B202 (iPhone; U; CPU OS 11_1_2 like Mac OS X; en_us)'

    def __init__(self):
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.dir = self.__find_config_dir(script_name)
        self.parser = self.__init_configparser(script_name)
        global DEBUG
        DEBUG = self.parser.getboolean('debug', DEBUG)
        global VERBOSE
        VERBOSE = self.parser.getboolean('verbose', VERBOSE)
        global VERIFY_SSL
        VERIFY_SSL = self.parser.getboolean('verify_ssl', VERIFY_SSL)

    @staticmethod
    def __find_config_dir(script_name):
        # use the script name minus any extension for the config directory
        config_dir = None
        searched_paths = list()
        for config_dir_base in ('.', os.path.join(os.environ['HOME'], '.config'), ):
            for config_dir_name in (script_name, '.' + script_name):
                d = os.path.join(config_dir_base, config_dir_name)
                searched_paths.append(d)
                if os.path.exists(d) and os.path.isdir(d):
                    config_dir = d
                    break
            if config_dir is not None:
                break
        if config_dir is None:
            print('No config directory found, using current directory. [searched: {}]'.format(','.join(searched_paths)))
            config_dir = '.'
        return config_dir

    def __init_configparser(self, script_name):
        # now look for config file
        parser = configparser.ConfigParser()
        parser.read_dict(Config.defaults)
        ini_file = os.path.join(self.dir, 'config')
        if os.path.exists(ini_file):
            LOG.debug("Reading config file: {}".format(ini_file))
            with open(ini_file, 'r') as f:
                config_string = '[{}]\n'.format(script_name) + f.read()
                parser.read_string(config_string)
        return parser[script_name]


class MLBConfig(Config):
    """This is a TODO."""
    # example: https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2017-08-10&endDate=2017-08-10&expand=schedule.teams,schedule.linescore,schedule.game.content.media.epg
    api_url = 'https://statsapi.mlb.com'
    # ?? mf_svc_url = 'https://mf.svc.nhl.com/ws/media/mf/v2.4/stream'
    # ?? ua_nhl = 'NHL/11479 CFNetwork/887 Darwin/17.0.0'

    def __init__(self):
        Config.__init__(self)
