mlbv - MLB stream viewer
========================

`mlbv` is a command-line interface to the MLB.tv service. It's primary purpose is to allow you to view game
streams on linux, including live streams, with a valid MLB tv subscription.  It also allows you to view game
status, results and schedules, stream highlights (recap and condensed games), and filter results based on
favourite teams.

Features:

* stream or record live or archived MLB games (requires MLB.tv subscription)
* show completed game highlights (condensed or recap) (no subscription required)
* display game schedules for given day or number of days
    - option to show or hide scores
* filter display based on favourite teams
* show standings


This project is inspired from the [MLBviewer](https://github.com/sdelafond/mlbviewer) project, although it
differs in that it does not provide an interactive interface. It strictly command-line based, although it does
offer quite a few options to view game-related data.  This project allows you to quickly find the game,
status, or highlights of your favourite team.

This package requires a valid MLB.tv subscription in order to view live or archived games. It is also subject
to local blackout restrictions. However, if you don't have a subscription you can still view game recaps or
condensed games.


Sample console output (with linescore enabled):

````
       2018-04-07                                        Series  | Score |   State   | Feeds
-----------------------------------------------------------------|-------|-----------|--------------
13:05: Baltimore (BAL) at NY Yankees (NYY)                 3/4   |  3-3  |  Bot 6th  | a/h     
         1  2  3  4  5  6  7  8  R  H  E                         |       |   0 out   | 
   BAL   0  0  2  1  0  0        3  4  0                         |       |           | 
   NYY   0  2  0  0  1           3  5  1                         |       |           | 
13:05: NY Mets (NYM) at Washington (WSH)                   2/3   |  1-2  |  Bot 6th  | a/h     
         1  2  3  4  5  6  7  8  R  H  E                         |       |   2 out   | 
   NYM   0  0  0  0  0  1        1  6  1                         |       |           | 
   WSH   0  0  0  0  1  1        2  4  1                         |       |           | 
13:05: Tampa Bay (TB) at Boston (BOS)                      2/3   |  2-8  |  Top 6th  | a/h     
         1  2  3  4  5  6  7  8  R  H  E                         |       |   1 out   | 
   TB    2  0  0  0  0           2  4  0                         |       |           | 
   BOS   4  4  0  0  0           8  6  0                         |       |           | 
14:10: Detroit (DET) at Chi White Sox (CWS)                2/3   |  0-0  |  Top 3rd  | a/h     
         1  2  3  4  5  6  7  8  R  H  E                         |       |   0 out   | 
   DET   0  0                    0  0  0                         |       |           | 
   CWS   0  0                    0  2  0                         |       |           | 
14:10: Seattle (SEA) at Minnesota (MIN)                    2/3   |  0-0  |  Top 4th  | a/h/mkt_a 
         1  2  3  4  5  6  7  8  R  H  E                         |       |   2 out   | 
   SEA   0  0  0                 0  0  0                         |       |           | 
   MIN   0  0  0                 0  1  0                         |       |           | 
14:15: Arizona (ARI) at St. Louis (STL)                    2/3   |  1-1  |  Bot 2nd  | a/h     
         1  2  3  4  5  6  7  8  R  H  E                         |       |   2 out   | 
   ARI   1  0                    1  1  0                         |       |           | 
   STL   1                       1  3  0                         |       |           | 
16:05: Chi Cubs (CHC) at Milwaukee (MIL)                   3/4   |       |           |         
16:10: Kansas City (KC) at Cleveland (CLE)                 2/3   |       |           |         
18:05: LA Dodgers (LAD) at San Francisco (SF)              1/2   |       |           |         
18:05: Miami (MIA) at Philadelphia (PHI)                   2/3   |       |           |         
19:05: Cincinnati (CIN) at Pittsburgh (PIT)                3/4   |       |           |         
19:10: San Diego (SD) at Houston (HOU)                     2/3   |       |           |         
20:05: Toronto (TOR) at Texas (TEX)                        2/3   |       |           |         
20:10: Atlanta (ATL) at Colorado (COL)                     2/3   |       |           |         
21:07: Oakland (OAK) at LA Angels (LAA)                    2/3   |       |           |         
````

Sample standings output:

````
   ========  Division  ========   W   L PCT   GB   WGB  Streak
   --- American League West ---
1  Houston Astros                 2   1 .667  -    -    [W1]
2  Los Angeles Angels             2   1 .667  -    -    [W2]
3  Seattle Mariners               1   1 .500  0.5  0.5  [L1]
4  Oakland Athletics              1   2 .333  1.0  1.0  [L2]
5  Texas Rangers                  1   2 .333  1.0  1.0  [L1]
   --- American League East ---
1  Boston Red Sox                 2   1 .667  -    -    [W2]
2  New York Yankees               2   1 .667  -    -    [L1]
3  Baltimore Orioles              1   1 .500  0.5  0.5  [L1]
4  Tampa Bay Rays                 1   2 .333  1.0  1.0  [L2]
5  Toronto Blue Jays              1   2 .333  1.0  1.0  [W1]
   --- American League Central ---
1  Chicago White Sox              2   0 1.000 -    -    [W2]
2  Cleveland Indians              1   1 .500  1.0  0.5  [W1]
3  Minnesota Twins                1   1 .500  1.0  0.5  [W1]
4  Detroit Tigers                 0   1 .000  1.5  1.0  [L1]
5  Kansas City Royals             0   2 .000  2.0  1.5  [L2]
   --- National League Central ---
1  Milwaukee Brewers              3   0 1.000 -    -    [W3]
2  Pittsburgh Pirates             1   0 1.000 1.0  -    [W1]
3  Chicago Cubs                   2   1 .667  1.0  -    [W1]
4  Cincinnati Reds                0   2 .000  2.5  1.5  [L2]
5  St. Louis Cardinals            0   2 .000  2.5  1.5  [L2]
   --- National League West ---
1  Arizona Diamondbacks           2   1 .667  -    -    [L1]
2  San Francisco Giants           2   1 .667  -    -    [L1]
3  Colorado Rockies               1   2 .333  1.0  1.0  [W1]
4  Los Angeles Dodgers            1   2 .333  1.0  1.0  [W1]
5  San Diego Padres               0   3 .000  2.0  2.0  [L3]
   --- National League East ---
1  New York Mets                  2   0 1.000 -    +0.5 [W2]
2  Washington Nationals           2   0 1.000 -    +0.5 [W2]
3  Atlanta Braves                 2   1 .667  0.5  -    [W1]
4  Miami Marlins                  1   2 .333  1.5  1.0  [L1]
5  Philadelphia Phillies          1   2 .333  1.5  1.0  [L1]
````

This project incorporates some code modified from the following projects: 

* [mlbstreamer](https://github.com/tonycpsu/mlbstreamer): a similar project. 
    - Session authentication code is taken shamelessly from this project.
* [Kodi plugin.video.mlbtv](https://github.com/eracknaphobia/plugin.video.mlbtv)


## Pre-Requisites:

`mlbv` requires the following software to be installed and configured:

* python 
    - python v3 (tested with 3.6) 
* python modules (installed by `pip install`):
    - [requests](http://python-requests.org/) module 
    - [python-dateutil](https://dateutil.readthedocs.io/en/stable/) module
    - [python-lxml](http://lxml.de/) module
* [streamlink](https://streamlink.github.io/)
* a video player. Either `vlc` or `mpv` is recommended.

This software is tested under linux. It should work under Windows or Mac with the pre-requisites installed, but may require minor tweaks (bug reports are welcome).


## Installation

1. Clone this repository.
2. Run `pip install .`
3. Run `mlbv --init` to create a configuration directory and populate the `config` file
   with defaults and the required MLB.tv username and password.


## Configuration

An example `config` file is provided in the repository. You can run `mlbv --init` to copy the config file into
a local config directory (which will be created) and then populate it with the prompted MLB.tv username and password.
The `config` file will be located at `$HOME/.config/mlbv/config`. The directories are created if necessary.

The properties in the config file are documented in the file itself. If you want to stream live or archived
games then you must provide valid login credentials (if you don't have MLB.tv you can still see scores and
watch highlights).

Some things you may want to set in the `config` file:

* `username`: MLB.tv account username
* `password`: MLB.tv account password
* `favs`: a comma-separated list of team codes which are 1) highlighted in the game data and 2) can be filtered on using the --filter option to show only the favourite team(s)
* `scores`: a boolean specifying whether or not you want to see scores in the game information. Warning: spoilers!
* `resolution`: the stream quality (passed in to streamlink). Use 'best' for full HD at 60 frames/sec.
    - others options are: 'worst', '360p', '540p', '720p_alt', '720p', 'best'


## Usage

Help is available by running:

    mlbv --help

Running `mlbv` without options shows you the status of today's games, including scores unless you've
configured to hide scores by default.

#### Usage note: shorter arguments

In general, you can shorten the long option names down to something unique. 

For example, rather than having to type `--yesterday` you can shorten it right down to `--y`.
However, you can one shorten `--tomorrow` down to `--to` since there is also the `--team` option which matches
up to `--t`.


### Playing a Live or Archived Game

If you pass the `-t/--team TEAM` option, the game stream (live or archived) is launched for the given team. By
default the local feed for the given team is chosen - i.e., it will follow the home/away feed appropriate for
the team so that you get the local team feed.  You can override the feed using the `-f/--feed` option. This
works for either live games or for archived games (e.g. if you use the `--date` option to select an earlier date).

Example:

    mlbv --team tor          # play the live Blue Jays game
    mlbv --yesterday -t tor  # play yesterday's Blue Jays game (see below for options on specifying dates)


#### Controlling where the stream starts

You can start from the top or bottom of an inning:

    mlbv --team tor --inning t5  # start from top of 5th
    mlbv --team tor --inning b5  # start from bottom of 5th

This works for either live or archived games.

For a live game, you can start from the beginning with:

    mlbv --team tor --from-start  # start stream at beginning, live games only


#### Doubleheaders

If a game is a doubleheader then you can select the second game using the `-g/--game` argument. 
By default it will select the first game.


### Fetching

If you pass the `-f/--fetch` option, instead of launching the video player, the selected stream is saved to
disk. The stream is named to convention: `<date>-<away_team>-<home_team>-<feed>.ts`.

- Live games have extension `.ts`, highlight games are `.mp4`


Example: `2018-03-31-nyy-tor-home.ts`.

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
    mlbv --team tor -f recap

NOTE: You don't need login credentials to play highlights.

#### Watching Multiple Game Recaps (for a given day)

You can start watching a series of game recaps for a given day using the `--recaps` option. This option shows game
recaps for either all games or for a selected set of teams.

Example:

    mlbv --recaps                       # show all available game recaps for today's games
    mlbv --yesterday --recaps           # show all available game recaps for yesterday's games
    mlbv --yesterday --recaps tor,wsh   # show game recaps for yesterday's Toronto, Boston games
    mlbv --yesterday --recaps tor,wsh --fetch   # same as above but save to disk instead of view


### Specifying Dates

You can specify the date to view using one of the following:

    -d|--date yyyy-mm-dd    # specific date
    --yesterday (or --yes)  # shortcut to yesterday
    --tomorrow  (or --tom)  # shortcut to tomorrow

For listing game data only (doesn't make sense for viewing), you can specify a number of days using the
`--days DAYS` option. Use this to show a schedule. It's useful with the `--filter` option to filter based on
favourite team(s).


### Standings

You can display standings via the `--standings` option. This option displays the given standings category then
exits.

Standings categories:

* all
* division
* conference
* wildcard
* league
* postseason
* preseason

By default, the division standings are displayed for today's date. 
You can add the `-d/--date yyyy-mm-dd` option to show standings for any given date.

You don't have to specify the full standings category, it will match any substring given. e.g. `--standings d`
will match division or `--standings wild` will match wildcard.


## Examples

Note: the common options have both short and long options. Both are shown in these examples.


#### Live Games

    mlbv --team tor               # play the live Jays game. The feed is chosen based on Jays being home vs. away
    mlbv -t tor --feed national   # play live game, choose the national feed
    mlbv -t tor --feed away       # play live game, choose the away feed. If the Jays are the home team this would choose
                                  # the opponent's feed

#### Archived Games

    mlbv --yesterday -t tor        # play yesterday's Jays game
    mlbv --date 2018-03-31 -t tor  # watch the Jays beat the Yankees #spoiler

#### Highlights

Use the `--feed` option to select the highlight feed (`recap` or `condensed`):

    mlbv --yesterday -t tor --feed condensed  # condensed feed
    mlbv --yesterday -t tor -f recap          # recap feed

You can also use the `--recaps` option to show highlights for games on given day.
This will show all chosen recaps, one-by-one until finished. A highlight reel.

    mlbv --yesterday --recaps all         # show all available recaps for yesterday games
    mlbv --yesterday --recaps --filter    # show recaps for favourites
    mlbv --yesterday --recaps tor,wsh,bos # show recaps for given set of teams
    mlbv --yesterday --recaps --fetch     # fetch all recaps

#### Fetch

In these examples the game is save to a `.ts` file in the current directory.

    mlbv --team tor --fetch
    mlbv --yesterday -t tor -f recap --fetch   # fetch yesterday's recap

#### Using `--days` for Schedule View

    mlbv --days 7           # show schedule for upcoming week
    mlbv --days 7 --filter  # show schedule for upcoming week, filtered on favourite teams (from config file)
    mlbv --days 7 --filter --favs 'tor,wsh' # show schedule filtered on favourite teams (from option)

#### Linescores

    mlbv -l        # show linescores for today
    mlbv --yes -l  # show linescores for yesterday
    mlbv --date 2018-03-29 --linescore --days 7 --filter  # show linescores for favs in week 1

#### Standings

    mlbv --standings           # display division standings
    mlbv --standings division  # display division standings
    mlbv --standings div       # display division standings (shortened name)
    mlbv --standings league    # display overall league standings
    mlbv --standings all       # display all regular season standings categories

    mlbv --standings --date 2015-10-01  # display division standings for Oct 1, 2015

