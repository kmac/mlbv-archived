#!/usr/bin/env python
"""
This project provides a CLI interface into streaming MLB games from MLB.com

Links: http://statsapi.mlb.com/docs/

https://github.com/tonycpsu/mlbstreamer - a similar project

"""

import argparse
import inspect
import logging
import os
import subprocess
import sys
import time

from datetime import datetime
from datetime import timedelta

import mlbv.mlbam.common.config as config
import mlbv.mlbam.common.gamedata as gamedata
import mlbv.mlbam.common.util as util
import mlbv.mlbam.mlbconfig as mlbconfig
import mlbv.mlbam.mlbgamedata as mlbgamedata
import mlbv.mlbam.standings as standings
import mlbv.mlbam.mlbstream as mlbstream


LOG = None  # initialized in init_logging


HELP_HEADER = """MLB game tracker and stream viewer.
"""
HELP_FOOTER = """Use --usage for full usage instructions and pre-requisites.

Filters:
    For the --filter option use either the built-in filters (see --list-filters) or
    provide your own list of teams, separated by comma: e.g. tor,bos,nyy

Feed Identifiers:
    You can use either the short form feed identifier or the long form:
    {feedhelp}""".format(feedhelp=gamedata.get_feedtype_keystring(mlbgamedata.FEEDTYPE_MAP))


def display_usage():
    """Displays contents of readme file."""
    current_dir = os.path.dirname(inspect.getfile(inspect.currentframe()))
    readme_path = os.path.abspath(os.path.join(current_dir, '..', 'README.md'))
    if not os.path.exists(readme_path):
        print("Could not find documentation file [expected at: {}]".format(readme_path))
        return -1
    if 'PAGER' in os.environ:
        cmd = [os.environ['PAGER'], readme_path]
        subprocess.run(cmd)
    else:
        with open(readme_path, 'r') as infile:
            for line in infile:
                print(line, end='')
    return 0


def main(argv=None):
    """Entry point for mlbv"""

    # using argparse (2.7+) https://docs.python.org/2/library/argparse.html
    parser = argparse.ArgumentParser(description=HELP_HEADER, epilog=HELP_FOOTER,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--init", action="store_true",
                        help="Generates a config file using a combination of defaults plus prompting for MLB.tv credentials.")
    parser.add_argument("--usage", action="store_true", help="Display full usage help.")
    parser.add_argument("-d", "--date", help="Display games/standings for date. Format: yyyy-mm-dd")
    parser.add_argument("--days", type=int, default=1, help="Number of days to display")
    parser.add_argument("--tomorrow", action="store_true", help="Use tomorrow's date")
    parser.add_argument("--yesterday", action="store_true", help="Use yesterday's date")
    parser.add_argument("-t", "--team",
                        help="Play selected game feed for team, one of: {}".format(mlbgamedata.TEAM_CODES))
    parser.add_argument("-f", "--feed",
                        help=("Feed type, either a live/archive game feed or highlight feed "
                              "(if available). Available feeds are shown in game list,"
                              "and have a short form and long form (see 'Feed identifiers' section below)"))
    parser.add_argument("-r", "--resolution",
                        help=("Stream resolution for streamlink (overrides settting in config file). "
                              "Choices: {}. Can also be a comma-separated list of values (no spaces), "
                              "e.g 720p_alt,720p,540p").format(config.BANDWIDTH_CHOICES))
    parser.add_argument("-i", "--inning",
                        help=("Start live/archive stream from inning. Format: {t|b}{inning_num}. "
                              "t|b: (optional) top or bottom, inning_num: inning number. "
                              "e.g.  '5' - start at 5th inning. 't5' start at top 5th. "
                              "'b5' start at bottom 5th."))
    parser.add_argument("--inning-offset", type=int, metavar='SECS',
                        help="Override the inning offset time in seconds. Default=240 (4 minutes)")
    parser.add_argument("--from-start", action="store_true", help="Start live/archive stream from beginning")
    parser.add_argument("--favs", help=argparse.SUPPRESS)
                        # help=("Favourite teams, a comma-separated list of favourite teams " "(normally specified in config file)"))
    parser.add_argument("-o", "--filter", nargs='?', const='favs', metavar='filtername|teams',
                        help=("Filter output. Either a filter name (see --list-filters) or a comma-separated "
                              "list of team codes, eg: 'tor.bos,wsh'. Default: favs"))
    parser.add_argument("--list-filters", action='store_true', help="List the built-in filters")
    parser.add_argument("-g", "--game", default='1', choices=('1', '2'),
                        help="Select game number of double-header")
    parser.add_argument("-s", "--scores", action="store_true",
                        help="Show scores (default off; overrides config file)")
    parser.add_argument("-n", "--no-scores", action="store_true",
                        help="Do not show scores (default on; overrides config file)")
    parser.add_argument("-l", "--linescore", nargs='?', const='all', metavar='filter',
                        help="Show linescores. Optional: specify a filter as per --filter option.")
    parser.add_argument("--username", help=argparse.SUPPRESS)  # help="MLB.tv username. Required for live/archived games.")
    parser.add_argument("--password", help=argparse.SUPPRESS)  # help="MLB.tv password. Required for live/archived games.")
    parser.add_argument("--fetch", "--record", action="store_true", help="Save stream to file instead of playing")
    parser.add_argument("--wait", action="store_true",
                        help=("Wait for game to start (live games only). Will block launching the player until game time. "
                              "Useful when combined with the --fetch option."))
    parser.add_argument("--standings", nargs='?', const='division', metavar='[category]',
                        help=("Display standings. This option will display the selected standings category, then exit. "
                              "'[category]' is one of: '" + ', '.join(standings.STANDINGS_OPTIONS) + "' [default: %(default)s]. "
                              "The standings category can be shortened down to one character (all matching "
                              "categories will be included), e.g. 'div'. "
                              "Can be combined with -d/--date option to show standings for any given date.")
                        )
    parser.add_argument("--recaps", nargs='?', const='all', metavar='FILTER',
                        help=("Play recaps for given teams. "
                              "[FILTER] is an optional filter as per --filter option"))
    parser.add_argument("-v", "--verbose", action="store_true", help=argparse.SUPPRESS)  # help="Increase output verbosity")
    parser.add_argument("-D", "--debug", action="store_true", help=argparse.SUPPRESS)    # help="Turn on debug output")
    args = parser.parse_args()

    if args.usage:
        return display_usage()

    team_to_play = None
    feedtype = None

    if args.init:
        return config.Config.generate_config(args.username, args.password, "MLB.tv")

    # get our config
    config.CONFIG = config.Config(mlbconfig.DEFAULTS, args)

    # append log files if DEBUG is set (from top of file)
    util.init_logging(os.path.join(config.CONFIG.dir,
                                   os.path.splitext(os.path.basename(sys.argv[0]))[0] + '.log'), True)

    global LOG
    LOG = logging.getLogger(__name__)

    if args.list_filters:
        print('List of built filters: ' + ', '.join(sorted(mlbgamedata.FILTERS.keys())))
        return 0
    if args.debug:
        config.CONFIG.parser['debug'] = 'true'
    if args.verbose:
        config.CONFIG.parser['verbose'] = 'true'
    if args.username:
        config.CONFIG.parser['username'] = args.username
    if args.password:
        config.CONFIG.parser['password'] = args.password
    if args.inning_offset is not None:
        config.CONFIG.parser['stream_start_offset_secs'] = str(args.inning_offset)
    if args.team:
        team_to_play = args.team.lower()
        if team_to_play not in mlbgamedata.TEAM_CODES:
            # Issue #4 all-star game has funky team codes
            LOG.warning('Unexpected team code: %s', team_to_play)
    if args.feed:
        feedtype = gamedata.convert_to_long_feedtype(args.feed.lower(), mlbgamedata.FEEDTYPE_MAP)
    if args.resolution:
        config.CONFIG.parser['resolution'] = args.resolution
    if args.scores:
        config.CONFIG.parser['scores'] = 'true'
    elif args.no_scores:
        config.CONFIG.parser['scores'] = 'false'
    if args.linescore:
        if args.linescore != 'all':
            config.CONFIG.parser['filter'] = args.linescore
            # config.CONFIG.parser['favs'] = args.linescore
        config.CONFIG.parser['linescore'] = 'true'
    if args.favs:
        config.CONFIG.parser['favs'] = args.favs
    if args.filter:
        config.CONFIG.parser['filter'] = args.filter

    if config.DEBUG:
        LOG.info(str(config.CONFIG))
    else:
        LOG.debug(str(config.CONFIG))

    if args.yesterday:
        args.date = datetime.strftime(datetime.today() - timedelta(days=1), "%Y-%m-%d")
    elif args.tomorrow:
        args.date = datetime.strftime(datetime.today() + timedelta(days=1), "%Y-%m-%d")
    elif args.date is None:
        args.date = datetime.strftime(datetime.today(), "%Y-%m-%d")

    if args.standings:
        standings.get_standings(args.standings, args.date, args.filter)
        return 0

    gamedata_retriever = mlbgamedata.GameDataRetriever()

    # retrieve all games for the dates given
    game_day_tuple_list = gamedata_retriever.process_game_data(args.date, args.days)

    if team_to_play is None and not args.recaps:
        # nothing to play; display the games
        presenter = mlbgamedata.GameDatePresenter()
        displayed_count = 0
        for game_date, game_records in game_day_tuple_list:
            presenter.display_game_data(game_date, game_records, args.filter)
            displayed_count += 1
            if displayed_count < len(game_day_tuple_list):
                print('')
        return 0

    # from this point we only care about first day in list
    if len(game_day_tuple_list) > 0:
        game_date, game_data = game_day_tuple_list[0]
    else:
        # nothing to stream
        return 0

    if args.recaps:
        recap_teams = list()
        if args.recaps == 'all':
            for game_pk in game_data:
                # add the home team
                recap_teams.append(game_data[game_pk]['home']['abbrev'])
        else:
            for team in args.recaps.split(','):
                recap_teams.append(team.strip())
        for game_pk in game_data:
            game_rec = mlbgamedata.apply_filter(game_data[game_pk], args.filter)
            if game_rec and (game_rec['home']['abbrev'] in recap_teams or game_rec['away']['abbrev'] in recap_teams):
                if 'recap' in game_rec['feed']:
                    LOG.info("Playing recap for %s at %s", game_rec['away']['abbrev'].upper(), game_rec['home']['abbrev'].upper())
                    game_num = 1
                    if game_rec['doubleHeader'] != 'N':
                        game_num = game_rec['gameNumber']
                    stream_game_rec = mlbstream.get_game_rec(game_data, game_rec['home']['abbrev'], game_num)
                    mlbstream.play_stream(stream_game_rec, game_rec['home']['abbrev'], 'recap', game_date,
                                          args.fetch, None, None, is_multi_highlight=True)
                else:
                    LOG.info("No recap available for %s at %s", game_rec['away']['abbrev'].upper(), game_rec['home']['abbrev'].upper())
        return 0

    # LOG.info('Sorry, MLB.tv stream support is broken. You should switch to https://github.com/tonycpsu/streamglob')
    # return -1

    game_rec = mlbstream.get_game_rec(game_data, team_to_play, args.game)

    if args.wait and not util.has_reached_time(game_rec['mlbdate']):
        LOG.info('Waiting for game to start. Local start time is %s', util.convert_time_to_local(game_rec['mlbdate']))
        print('Use Ctrl-c to quit .', end='', flush=True)
        count = 0
        while not util.has_reached_time(game_rec['mlbdate']):
            time.sleep(10)
            count += 1
            if count % 6 == 0:
                print('.', end='', flush=True)

        # refresh the game data
        LOG.info('Game time. Refreshing game data after wait...')
        game_day_tuple_list = gamedata_retriever.process_game_data(args.date, 1)
        if len(game_day_tuple_list) > 0:
            game_date, game_data = game_day_tuple_list[0]
        else:
            LOG.error('Unexpected error: no game data found after refresh on wait')
            return 0

        game_rec = mlbstream.get_game_rec(game_data, team_to_play, args.game)

    return mlbstream.play_stream(game_rec, team_to_play, feedtype, args.date, args.fetch, args.from_start, args.inning)


if __name__ == "__main__" or __name__ == "main":
    sys.exit(main())

# vim: set filetype=python
