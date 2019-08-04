"""
Configuration
"""

import configparser
import inspect
import logging
import os
import sys


HIGHLIGHT_FEEDTYPES = ('condensed', 'recap')

# Note: 720p_alt is the 60fps stream
BANDWIDTH_CHOICES = ('worst', '224p', '288p', '360p', '504p', '540p', '720p', '720p_alt', 'best')

CONFIG = None  # holds a Config instance

# These are initialized/updated via the Config class
DEBUG = False
VERBOSE = False
VERIFY_SSL = True
SAVE_JSON_FILE = True
SAVE_JSON_FILE_BY_TIMESTAMP = False  # normally false; will save many .json files if set
SAVE_PLAYLIST_FILE = False
UNICODE = True
DEFAULT_STREAM_START_OFFSET_SECS = 0

LOG = logging.getLogger(__name__)


class Config:
    """Contains the configuration data for use within the application, including a configparser instance
    for pulling in configuration from the 'config' file."""
    config_dir_roots = ('.', os.path.join(os.path.expanduser('~'), '.config'))

    # TODO move these into parser, add defaults to mlbgamedata.py:
    platform = 'IPHONE'
    ua_pc = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.97 Safari/537.36'
    ua_iphone = 'AppleCoreMedia/1.0.0.15B202 (iPhone; U; CPU OS 11_1_2 like Mac OS X; en_us)'

    def __init__(self, defaults, args):
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        self.defaults = defaults
        self.dir = self.__find_config_dir(script_name)
        self.parser = self.__init_configparser(script_name)
        global DEBUG
        DEBUG = self.parser.getboolean('debug', DEBUG) or args.debug
        global VERBOSE
        VERBOSE = self.parser.getboolean('verbose', VERBOSE) or args.verbose
        global VERIFY_SSL
        VERIFY_SSL = self.parser.getboolean('verify_ssl', VERIFY_SSL)
        global UNICODE
        UNICODE = self.parser.getboolean('unicode', UNICODE)
        if DEBUG:
            # Turn on some extras
            global SAVE_PLAYLIST_FILE
            SAVE_PLAYLIST_FILE = True
            global SAVE_JSON_FILE_BY_TIMESTAMP
            SAVE_JSON_FILE_BY_TIMESTAMP = True

    @staticmethod
    def __find_config_dir(script_name):
        # use the script name minus any extension for the config directory
        config_dir = None
        searched_paths = list()
        for config_dir_base in Config.config_dir_roots:
            for config_dir_name in (script_name, '.' + script_name):
                test_dir = os.path.join(config_dir_base, config_dir_name)
                searched_paths.append(test_dir)
                if os.path.exists(test_dir) and os.path.isdir(test_dir) and os.path.exists(os.path.join(test_dir, 'config')):
                    config_dir = test_dir
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
        parser.read_dict(self.defaults)
        ini_file = os.path.join(self.dir, 'config')
        if os.path.exists(ini_file):
            LOG.debug("Reading config file: %s", ini_file)
            with open(ini_file, 'r') as openf:
                config_string = '[{}]\n'.format(script_name) + openf.read()
                parser.read_string(config_string)
        return parser[script_name]

    @staticmethod
    def generate_config(username=None, password=None, servicename="MLB.tv"):
        """Creates config file from template + user prompts."""
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        # use the script name minus any extension for the config directory
        config_dir = None
        config_dir = os.path.join(Config.config_dir_roots[1], script_name)
        if not os.path.exists(config_dir):
            print("Creating config directory: {}".format(config_dir))
            os.makedirs(config_dir)
        config_file = os.path.join(config_dir, 'config')
        if os.path.exists(config_file):
            print("Aborting: The config file already exists at '{}'".format(config_file))
            return False

        # copy the template config file
        print("Generating basic config file at: {}".format(config_dir))
        current_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
        template_config_path = os.path.abspath(os.path.join(current_dir, '../../..', 'config.template'))
        if not os.path.exists(template_config_path):
            print("Could not find template config file [expected at: {}]".format(template_config_path))
            return False

        if username is None:
            username = input('Enter {} username: '.format(servicename))
        if password is None:
            password = input('Enter {} password: '.format(servicename))

        with open(template_config_path, 'r') as infile, open(config_file, 'w') as outfile:
            for line in infile:
                if line.startswith('# username='):
                    outfile.write("username={}\n".format(username))
                elif line.startswith('# password='):
                    outfile.write("password={}\n".format(password))
                else:
                    outfile.write(line)
        print("Finished creating config file: {}".format(config_file))
        print("You may want to edit it now to set up favourites, etc.")
        return True

    def __str__(self):
        strs = list()
        for (name, val) in (('dir', self.dir), ('DEBUG', DEBUG), ('VERBOSE', VERBOSE),
                            ('DEFAULT_STREAM_START_OFFSET_SECS', DEFAULT_STREAM_START_OFFSET_SECS),
                            ):
            strs.append("{}={}".format(name, val))
        for (name, val) in self.parser.items():
            if name != 'password':
                strs.append("{}={}".format(name, val))
        return 'Config: ' + ', '.join(strs)
