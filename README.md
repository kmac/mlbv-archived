nhlv - NHL viewer
=================

`nhlv` is a command-line interface to the NHL.tv service. It's primary purpose is to allow you to view game
streams on linux, including live streams with a valid NHL tv/gamecenter subscription.  It also allows you to
view game status, results and schedules, stream highlights (recap and condensed games), and filter results
based on favourite teams.

This project is inspired from the MLB baseball [MLBviewer](https://github.com/sdelafond/mlbviewer) project,
although it differs in that it does not provide an interactive interface (that may be added in future releases). 

For some reason the MLB/NHL does not support viewing live games on linux. There is an excellent kodi
[plugin](https://github.com/eracknaphobia/plugin.video.nhlgcl) available, but I find Kodi to be a little heavy
to run from a laptop. This project, like MLBviewer for baseball, allows you to quickly find the game, status,
or highlights of your favourite team.

In order to view live or archived games, this package requires a valid NHL.tv subscription requirements. It
is also subject to local blackout restrictions. However, if you don't have a subscription you can still view
game recaps or condensed games.


Sample console output:

````
       2017-12-28                                                | Score |   State   | Feeds
-----------------------------------------------------------------|-------|-----------|------------
Live Games:                                                      |       |           |
19:30: Boston Bruins (BOS) at Washington Capitals (WSH)          |  3-3  | End OT    | away, french, national
21:00: Toronto Maple Leafs (TOR) at Arizona Coyotes (ARI)        |  3-2  | 11:40 2nd | away, home
22:00: Chicago Blackhawks (CHI) at Vancouver Canucks (VAN)       |  0-1  | 11:26 1st | away, national
22:00: Vegas Golden Knights (VGK) at Los Angeles Kings (LAK)     |  0-0  | 20:00 1st | national
-----                                                            |       |           |
22:30: Calgary Flames (CGY) at San Jose Sharks (SJS)             |       |           | away, home
19:30: Montréal Canadiens (MTL) at Tampa Bay Lightning (TBL)     |  1-3  | Final     | away, french, home
19:30: Philadelphia Flyers (PHI) at Florida Panthers (FLA)       |  2-3  | Final     | away, home

````

This project incorporates some code modified from the following projects: 

* https://github.com/eracknaphobia/plugin.video.nhlgcl (Kodi plugin)
* https://github.com/NHLGames/nhl.py


## Pre-Requisites:

`nhlv` requires the following software to be installed and configured:

* python 
    - python v3 (tested with 3.6) 
* python modules:
    - [requests](http://python-requests.org/) module 
    - [python-dateutil](https://dateutil.readthedocs.io/en/stable/) module
* [streamlink](https://streamlink.github.io/)
* a video player. Either `vlc` or `mpv` is recommended.


Note on installing python modules: 

Install via `pip` (preferably using virtualenv):

    pip install requests
    pip install python-dateutil

This software is tested under linux. It should work under Windows or Mac with the pre-requisites installed, but may require minor tweaks.


## Installation

1. Install the pre-requisites: 
    * Python 3.x is required
    * Install the python-requests module (via pip or your distribution's package manager) 
    * Install streamlink, which is required to view the HLS streams

2. Clone this repository.


## Configuration

An example config file is provided in the repository. The properties in the config file are documented. If you
want to stream live or archived games, you must provide valid login credentials. 

Some things you may want to set:

* username: NHL.tv account username
* password: NHL.tv account password
* use_rogers: set to true if your NHL streaming account goes through Rogers
* favs: a comma-separated list of team codes which are 1) highlighted in the game data and 2) can be filtered on using the --filter option to show only the favourite team(s)
* scores: a boolean specifying whether or not you want to see scores in the game information. Spoilers.
* resolution: the stream quality (passed in to streamlink). Use 'best' for full HD at 60 frames/sec.
    - others options are: 'worst', '360p', '540p', '720p_alt', '720p', 'best'


## TODO

* add `mlbv` to view baseball games. This should be fairly simple since they both use the MLBAM infrastructure.


## Usage

Help is available by running:

    nhlv --help

Running `nhlv` without options shows you the status of today's games.


### Playing a Live or Archived Game

If you pass the `-t/--team TEAM` option, the stream is launched for the given team. By default the local feed
for the given team is chosen - i.e., it will follow the home/away feed appropriate for the team so that you
get the local team feed.  You can override the feed using the `-f/--feed` option. This works for either live
games or for archived games (e.g. if you use the `--date` option to select an earlier date).

Example:

    nhlv --team wpg          # play the live jets game
    nhlv --yesterday -t wpg  # play yesterday's jets game (see below for options on specifying dates)


### Fetching

If you pass the `-f/--fetch` option, instead of launching the video player, the selected stream is saved to
disk. The stream is named to convention: `<date>-<away_team>-<home_team>-<feed>.mp4`. 

Example: `2017-12-27-edm-wpg-national.mp4`.

You can select the stream for fetch, then manually launch your video player at a later time while the
stream is being saved to file. 

Example:

    nhlv --team wpg --fetch  # fetch the live jets game to disk. Most players let you view while downloading


### Highlights: Recap or Condensed Games

Playing the game highlight is triggered by using the `-f/--feed` option. The `recap` or `condensed` feeds show
up after a game has ended. To watch the highlight, specify one of those feeds along with the team name in the
`-t/--team` option.

Example:

    nhlv --team wpg --f condensed

You don't need login credentials to play highlights.


### Specifying Dates

You can specify the date to view using one of the following:

    -d|--date yyyy-mm-dd    # specific date
    --yesterday (or --yes)  # shortcut to yesterday
    --tomorrow  (or --tom)  # shortcut to tomorrow

For listing game data only (doesn't make sense for viewing), you can specify a number of days using the
`--days DAYS` option. Use this to show a schedule. It's useful with the `--filter` option to filter based on
favourite team(s).


### Examples

Note: the common options have both short and long options. Both are shown in these examples.


#### Live Games

    nhlv --team wpg               # play the live jets game. The feed is chosen based on jets being home vs. away
    nhltv -t wpg --feed national  # play live game, choose the national feed
    nhltv -t wpg --feed away      # play live game, choose the away feed. If jets are the home team this would choose
                                  # the opponent's feed

#### Archived Games

    nhlv --yesterday -t wpg         # play yesterday's jets game
    nhltv --date 2017-12-27 -t wpg  # watch the jets beat the oilers #spoiler

#### Highlights

Use the `--feed` option to select the highlight feed (`recap` or `condensed`):

    nhlv --yesterday -t wpg --feed condensed  # condensed feed
    nhlv --yesterday -t wpg -f recap          # recap feed

#### Fetch

In these examples the game is save to a .mp4 file in the current directory.

    nhlv --team wpg --fetch
    nhlv --yesterday -t wpg -f recap --fetch   # fetch yesterday's recap

#### Using `--days` for Schedule View

    nhlv --days 7           # show schedule for upcoming week
    nhlv --days 7 --filter  # show schedule for upcoming week, filtered on favourite teams (from config file)
    nhlv --days 7 --filter --favs 'wpg,ott' # show schedule filtered on favourite teams (from option)

