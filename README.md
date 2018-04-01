mlbv - MLB viewer
=================

`mlbv` is a command-line interface to the MLB.tv service. It's primary purpose is to allow you to view game
streams on linux, including live streams, with a valid MLB tv subscription.  It also allows you to view game
status, results and schedules, stream highlights (recap and condensed games), and filter results based on
favourite teams.

This project is inspired from the [MLBviewer](https://github.com/sdelafond/mlbviewer) project, although it
differs in that it does not provide an interactive interface. It strictly command-line based, although it does
offer quite a few options to view game-related data.  This project allows you to quickly find the game,
status, or highlights of your favourite team.

This package requires a valid MLB.tv subscription in order to view live or archived games. It is also subject
to local blackout restrictions. However, if you don't have a subscription you can still view game recaps or
condensed games.


Sample console output:

````
2018-03-31                                                | Score |   State   | Feeds
-----------------------------------------------------------------|-------|-----------|--------------
Live Games:                                                      |       |           |
16:05: Houston (HOU) at Texas (TEX)                              |  9-3  |   End 9th | a/h/mkt_a
16:05: LA Angels (LAA) at Oakland (OAK)                          |  8-3  |   Bot 9th | a/h
18:10: Boston (BOS) at Tampa Bay (TB)                            |  2-0  |   Top 5th | a/h
19:05: Minnesota (MIN) at Baltimore (BAL)                        |  1-0  |   Top 2nd | a/h
19:10: Chi Cubs (CHC) at Miami (MIA)                             |  0-2  |   Top 2nd | a/h
19:10: Philadelphia (PHI) at Atlanta (ATL)                       |  2-1  |   Bot 1st | a/h
19:15: Chi White Sox (CWS) at Kansas City (KC)                   |  0-0  |   Top 1st | a/h
-----                                                            |       |           |
13:10: Pittsburgh (PIT) at Detroit (DET)                         |  0-0  | Postponed |
13:10: St. Louis (STL) at NY Mets (NYM)                          |  2-6  |     Final | a/h     cnd/rcp
14:10: Washington (WSH) at Cincinnati (CIN)                      | 13-7  |     Final | a/h     cnd/rcp
16:07: NY Yankees (NYY) at Toronto (TOR)                         |  3-5  |     Final | a/h
16:10: Cleveland (CLE) at Seattle (SEA)                          |  6-5  |   Bot 9th | a/h/mkt_h
20:10: Colorado (COL) at Arizona (ARI)                           |       |           |
20:40: Milwaukee (MIL) at San Diego (SD)                         |       |           |
21:10: San Francisco (SF) at LA Dodgers (LAD)                    |       |           |
````

This project incorporates some code modified from the following projects: 

* [mlbstreamer](https://github.com/tonycpsu/mlbstreamer)
* [Kodi plugin.video.mlbtv](https://github.com/eracknaphobia/plugin.video.mlbtv)


## Pre-Requisites:

`mlbv` requires the following software to be installed and configured:

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

* username: MLB.tv account username
* password: MLB.tv account password
* favs: a comma-separated list of team codes which are 1) highlighted in the game data and 2) can be filtered on using the --filter option to show only the favourite team(s)
* scores: a boolean specifying whether or not you want to see scores in the game information. Spoilers.
* resolution: the stream quality (passed in to streamlink). Use 'best' for full HD at 60 frames/sec.
    - others options are: 'worst', '360p', '540p', '720p_alt', '720p', 'best'


## Usage

Help is available by running:

    mlbv --help

Running `mlbv` without options shows you the status of today's games, including scores unless you've
configured to hide scores by default.


### Playing a Live or Archived Game

If you pass the `-t/--team TEAM` option, the stream is launched for the given team. By default the local feed
for the given team is chosen - i.e., it will follow the home/away feed appropriate for the team so that you
get the local team feed.  You can override the feed using the `-f/--feed` option. This works for either live
games or for archived games (e.g. if you use the `--date` option to select an earlier date).

Example:

    mlbv --team tor          # play the live Blue Jays game
    mlbv --yesterday -t tor  # play yesterday's Blue Jays game (see below for options on specifying dates)


### Fetching

If you pass the `-f/--fetch` option, instead of launching the video player, the selected stream is saved to
disk. The stream is named to convention: `<date>-<away_team>-<home_team>-<feed>.mp4`. 

Example: `2018-03-31-nyy-tor-home.mp4`.

You can select the stream for fetch, then manually launch your video player at a later time while the
stream is being saved to file. 

Example:

    mlbv --team tor --fetch  # Fetch the live jays game to disk. 
                             # Most video players let you view while downloading


### Highlights: Recap or Condensed Games

Playing the game highlight is triggered by using the `-f/--feed` option. The `recap` or `condensed` feeds show
up after a game has ended. To watch the highlight, specify one of those feeds along with the team name in the
`-t/--team` option.

Example:

    mlbv --team tor -f condensed

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

    mlbv --team tor               # play the live Jays game. The feed is chosen based on Jays being home vs. away
    nhltv -t tor --feed national  # play live game, choose the national feed
    nhltv -t tor --feed away      # play live game, choose the away feed. If the Jays are the home team this would choose
                                  # the opponent's feed

#### Archived Games

    mlbv --yesterday -t tor         # play yesterday's Jays game
    nhltv --date 2018-03-31 -t tor  # watch the Jays beat the Yankees #spoiler

#### Highlights

Use the `--feed` option to select the highlight feed (`recap` or `condensed`):

    mlbv --yesterday -t tor --feed condensed  # condensed feed
    mlbv --yesterday -t tor -f recap          # recap feed

#### Fetch

In these examples the game is save to a .mp4 file in the current directory.

    mlbv --team tor --fetch
    mlbv --yesterday -t tor -f recap --fetch   # fetch yesterday's recap

#### Using `--days` for Schedule View

    mlbv --days 7           # show schedule for upcoming week
    mlbv --days 7 --filter  # show schedule for upcoming week, filtered on favourite teams (from config file)
    mlbv --days 7 --filter --favs 'tor,wsh' # show schedule filtered on favourite teams (from option)

