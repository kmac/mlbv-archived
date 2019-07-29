mlbv - MLB stream viewer
========================

## UPDATE: MLBv is fixed!

It currently *heavily* borrows from [streamglob](https://github.com/sdelafond/streamglob), and you should probably
use that. The problem is that some dependencies used by streamglob are incompatible with Windows. MLBv works with
Windows, so this is the place to be until streamglob sorts out Windows compatibility.

There is currently a ton of repeated, unused, and sloppy code which was taken from streamglob, so feel free to
contribute.

----



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


Sample console output (default, no linescore):

````
       2018-04-10 Tue                            Series  │ Score │   State   │ Feeds
─────────────────────────────────────────────────────────┼───────┼───────────┼────────────────
14:10: Tampa Bay (TB) at Chi White Sox (CWS)       2/3   │  6-5  │ Final     │ a,h cnd,rcp
14:20: Pittsburgh (PIT) at Chi Cubs (CHC)          1/3   │  8-5  │ Final     │ a,h,ima cnd,rcp
18:10: Detroit (DET) at Cleveland (CLE)            2/4   │  1-2  │ Final     │ a,h cnd,rcp
19:05: Atlanta (ATL) at Washington (WSH)           2/3   │  1-4  │ Final     │ a,h cnd,rcp
19:05: Cincinnati (CIN) at Philadelphia (PHI)      2/3   │  1-6  │ Final     │ a,h cnd,rcp
19:05: Toronto (TOR) at Baltimore (BAL)            2/3   │  2-1  │ Final     │ a,h cnd,rcp
19:10: NY Mets (NYM) at Miami (MIA)                2/3   │  8-6  │ Final     │ a,h cnd,rcp
19:10: NY Yankees (NYY) at Boston (BOS)            1/3   │ 1-14  │ Final     │ a,h cnd,rcp
20:05: LA Angels (LAA) at Texas (TEX)              2/3   │ 11-1  │ Final     │ a,h cnd,rcp
20:10: Houston (HOU) at Minnesota (MIN)            2/3   │  1-4  │ Final     │ a,h,ima cnd,rcp
20:15: Milwaukee (MIL) at St. Louis (STL)          2/3   │  3-5  │ Final(11) │ a,h cnd,rcp
20:15: Seattle (SEA) at Kansas City (KC)           2/3   │  8-3  │ Final     │ a,h,ima cnd,rcp
20:40: San Diego (SD) at Colorado (COL)            2/3   │  5-2  │ Final     │ a,h,imh cnd,rcp
22:10: Oakland (OAK) at LA Dodgers (LAD)           1/2   │  0-4  │ Final     │ a,h cnd,rcp
22:15: Arizona (ARI) at San Francisco (SF)         2/3   │  4-5  │ Final     │ a,h cnd,rcp
````

Linescore output:

````
       2018-04-10 Tue
───────────────────────────────────────────────────────────────────────────────────────────
19:05: Toronto (TOR) at Baltimore (BAL)                  1  2  3  4  5  6  7  8  9  R  H  E
2/3    Final: 2-1                                  TOR   0  0  0  0  0  0  0  1  1  2  7  0
       Feeds: a,h cnd,rcp                          BAL   0  0  0  0  0  0  0  1  0  1  3  2
───────────────────────────────────────────────────────────────────────────────────────────
````

Standings output:

````
   ═════════ Division ═════════   W   L PCT   GB   WGB  Streak
   ─── American League West ────────────────────────────────
1  Los Angeles Angels            12   3 .800  -    -    [W6]
2  Houston Astros                10   4 .714  1.5  +1.0 [W1]
3  Seattle Mariners               7   4 .636  3.0  0.5  [W3]
4  Oakland Athletics              5   9 .357  6.5  4.0  [L1]
5  Texas Rangers                  4  11 .267  8.0  5.5  [L5]
   ─── American League East ────────────────────────────────
1  Boston Red Sox                11   2 .846  -    -    [W2]
2  Toronto Blue Jays              9   5 .643  2.5  -    [W1]
3  New York Yankees               7   7 .500  4.5  2.0  [W1]
4  Baltimore Orioles              5   9 .357  6.5  4.0  [L1]
5  Tampa Bay Rays                 3  10 .231  8.0  5.5  [L2]
   ─── American League Central ─────────────────────────────
1  Minnesota Twins                7   4 .636  -    -    [W3]
2  Cleveland Indians              8   6 .571  0.5  1.0  [L1]
3  Chicago White Sox              4   8 .333  3.5  4.0  [L1]
4  Detroit Tigers                 4   9 .308  4.0  4.5  [L5]
5  Kansas City Royals             3   9 .250  4.5  5.0  [L4]
   ─── National League Central ─────────────────────────────
1  Pittsburgh Pirates             9   4 .692  -    -    [L1]
2  Milwaukee Brewers              7   7 .500  2.5  1.0  [L1]
3  St. Louis Cardinals            7   7 .500  2.5  1.0  [W2]
4  Chicago Cubs                   6   7 .462  3.0  1.5  [L2]
5  Cincinnati Reds                2  11 .154  7.0  5.5  [L6]
   ─── National League West ────────────────────────────────
1  Arizona Diamondbacks          10   3 .769  -    -    [W2]
2  Colorado Rockies               8   7 .533  3.0  0.5  [W3]
3  San Francisco Giants           6   7 .462  4.0  1.5  [L1]
4  Los Angeles Dodgers            4   8 .333  5.5  3.0  [L2]
5  San Diego Padres               5  10 .333  6.0  3.5  [W1]
   ─── National League East ────────────────────────────────
1  New York Mets                 11   1 .917  -    -    [W9]
2  Atlanta Braves                 8   5 .615  3.5  +0.5 [W2]
3  Philadelphia Phillies          7   5 .583  4.0  -    [W4]
4  Washington Nationals           6   8 .429  6.0  2.0  [L3]
5  Miami Marlins                  4   9 .308  7.5  3.5  [W1]
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
    - Note: player can be specified via config file. If player is not on the system path you may need to
      setup the full path in the config file.

This software is tested under linux. It should work under Windows or Mac with the pre-requisites installed,
but may require minor tweaks (bug reports are welcome).


## 1. Installation

### Via pip

This project is on the Python Package Index (Pypi) at [mlbv](https://pypi.org/project/mlbv), and can be
installed using `pip`.

1. Run `pip install mlbv`
2. Run `mlbv --init` to create a configuration directory and populate the `config` file
   with defaults and the required MLB.tv username and password. See the next section for more details.

### Archlinux

Install `mlbv` via the AUR.


## 2. Configuration

After installing, run:

    mlbv --init

This will create the initial config file/directory and populate it with the prompted MLB.tv username and password.
The `config` file will be located at `$HOME/.config/mlbv/config`. Directories are created if necessary.

Other properties in the config file are documented in the file itself. If you want to stream live or archived
games then you must provide valid login credentials (if you don't have MLB.tv you can still see scores and
watch highlights).

Some properties you may want to set in the `config` file:

* `username`: MLB.tv account username
* `password`: MLB.tv account password
* `favs`: a comma-separated list of team codes which:
    - 1) are highlighted in the game data, and 
    - 2) are used for the default filter in the `-o/--filter` option (to show only the favourite team(s))
* `scores`: a boolean specifying whether or not you want to see scores in the game information. Warning: spoilers!
* `resolution`: the stream quality (passed in to streamlink). Use '720p_alt' for full HD at 60 frames/sec.
    - options are: 'worst', '224p', '288p', '360p', '504p', '540p', '720p', '720p_alt', 'best'
* `linescore`: to enable linescores by default (if scores are enabled)


## 3. QUICKSTART

Here's a quick overview of the most common usage options:

    mlbv               # show today's schedule/scores
    mlbv -l            # show today's linescores
    mlbv -t tor        # play today's Jays game, either live (if in-progress), or from the start (if archived)
    mlbv --recaps      # play all of today's recaps
    mlbv --standings   # show current standings


Help is available by running:

    mlbv --help   # short help
    mlbv --usage  # view full documenation
 

## 4. Default Behaviour: Show Schedule/Scores

Running `mlbv` by itself shows you the status of today's games, including scores (unless you've configured to hide scores by default).

### Scores/No-Scores

The `scores` option in the config file controls whether or not scores are shown. If false then no scores are
shown. Scores are also not shown before a feed is launched.

You can temporarily override the config file using either `-s/--scores` or `-n/--no-scores` options.


### Linescores

Linescores are displayed using the `-l/--linescore` option. You can also make linescores the default in the config file.

Since linescores take up more screen real estate it can be useful to combine them with a filter to limit the number of games shown. 


### Dates and Filters

See the sections below on Dates and Filters for more information on specifying dates and filtering output based on
league, division, favourites, or arbitrary teams.


> Note on Arguments
> 
> Frequently used arguments have both a long form with double-dash `--` argument and a short form which uses a single dash `-`. 
> 
> For the long form arguments, you can shorten any option name down to the shortest unique value.  For example,
> rather than having to type `--yesterday` you can shorten it right down to `--y`.  However, you can only
> shorten `--tomorrow` down to `--to` since there is also the `--team` option (which makes `--t` non-unique).


## 5. Watching a Live or Archived Game

Watching a game is triggered by the `-t/--team TEAM` option. With this option the game stream (live or
archived) is launched for the given team. 

When passing `-t/--team TEAM` option, the stream is launched for the given team. By default the local feed
for the given team is chosen - i.e., it will follow the home/away feed appropriate for the team so that you
get the local team feed.  You can override the feed using the `-f/--feed` option. This works for either live
games or for archived games (e.g. if you use the `--date` option to select an earlier date).

Example:

    mlbv --team tor          # play the live Blue Jays game
    mlbv --yesterday -t tor  # play yesterday's Blue Jays game (see below for options on specifying dates)


### Feed Selection

By default the local feed for the given team is chosen - i.e., it will follow the home/away feed appropriate
for the given team so that you get the team's local feed if available.  You can override the feed using the
`-f/--feed` option. This works for either live games or for archived games (e.g. if you use the `--date`
option to select an earlier date).

    mlbv --team tor --feed away  # choose the away feed (assuming Toronto is the home team, you will get the
                                 # opposing team's feed)


### Specifying Stream Start Location

For an in-progress game, the stream will join the live game at the current time. Use either  `--from-start` or
the `--inning/-i` option to override this behaviour.

For an archived game, the stream will start from the beginning.


#### Start from Inning

For both live and archived games you can start from the top or bottom of an inning:

    mlbv --team tor --inning t5  # start from top of 5th
    mlbv -t tor -i t5            # same thing but with short switches
    mlbv --team tor --inning b5  # start from bottom of 5th


#### Start from Beginning (Live Game)

For a live game, you can start from the beginning with:

    mlbv --team tor --from-start  # start stream at beginning, live games only


### Doubleheaders

If a game is a doubleheader then you can select the second game using the `-g/--game` argument. 
By default it will select the first game.


## 6. Record/Fetch

If you pass the `-f/--fetch` option, instead of launching the video player, the selected stream is saved to
disk. The stream is named to convention: `<date>-<away_team>-<home_team>-<feed>.ts`.

- Live games have extension `.ts`, highlight games are `.mp4`


Example: `2018-03-31-nyy-tor-home.ts`.

If your player supports it, you can select the stream to fetch, then manually launch your video player at a
later time while the stream is being saved to file. 

Example:

    mlbv --team tor --fetch  # Fetch the live jays game to disk. 
                             # Most video players allow you to view while downloading


## 7. Highlights: Recap or Condensed Games

Playing the game highlight is triggered by using the `-f/--feed` option. The `recap` or `condensed` feeds show
up after a game has ended. To watch the highlight, specify one of those feeds along with the team name in the
`-t/--team` option.

Example:

    mlbv --team tor -f condensed
    mlbv --team tor -f recap

NOTE: You don't need login credentials to play highlights.


### Playing Multiple Game Recaps (for a given day)

The `--recaps` option lets you select a batch of game recaps to watch for a given day.
This option shows game recaps either for all games or for a selected set of teams (using a filter).
If no argument is given to `recaps` then no filter is applied.

Usage:

    --recaps ?filter?  : filter is optional, if not supplied then all games are selected

Examples:

    mlbv --recaps                       # show all available game recaps for today's games
    mlbv --yesterday --recaps           # show all available game recaps for yesterday's games
    mlbv --yesterday --recaps ale       # show available game recaps for yesterday's games
                                        # in the American League East
    mlbv --yesterday --recaps tor,wsh   # show game recaps for yesterday's Toronto, Boston games
    mlbv --yesterday --recaps tor,wsh --fetch   # same as above but save to disk instead of view


## 8. Specifying Dates

You can specify the date to view using one of the following:

    -d|--date yyyy-mm-dd    # specific date
    --yesterday (or --yes)  # shortcut to yesterday
    --tomorrow  (or --tom)  # shortcut to tomorrow

For listing game data only (doesn't make sense for viewing), you can specify a number of days using the
`--days DAYS` option. Use this to show a schedule. It's useful with the `--filter` option to filter based on
favourite team(s).


## 9. Filters

You can filter the schedule/scores displays using the `-o/--filter` argument. 
The filter argument allows you to provide either a built-in filter name or a comma-separated list of team codes.

The filter option has the form:

    -o/--filter ?filter?  : where ?filter? is optional, and is either 
                            a 'filter name' or a comma-separated list of teams

> Note: -o is used as the short form because -f is taken. mnemonic: -o -> 'only'

> Note: Aside from the `--filter` command, other command arguments accept the same 'filter' string.
>       For example `--linescore ?filter?` and `--recaps ?filter?`


### Built-in Filters

If `?filter?` is not given then the built-in filter `favs` is used. `favs` is a filter which you can define 
in the config file to list your favourite team(s).

Other built-in filters are available which group teams by league and division. The filter names are:

* `al`, `ale`, `alc`, `alw` (American League, AL East, AL Central, AL West)
* `nl`, `nle`, `nlc`, `nlw` (National League, NL East, NL Central, NL West)

Using one of the above filter names will include those selected teams in the output.


### Ad-hoc Filters

You can also use any comma-separated list of team codes for a filter.

Examples:

    --filter tor            # single team filter
    --filter tor,bos,wsh    # multiple team filter
    -o tor,bos,wsh          # same as above using shorter `-o` form

Note: Do not use spaces between commas unless you encapsulate the list in quotes.


## 10. Standings

You can display standings via the `--standings [category]` option. This option displays the given standings category then exits.

You can also specify a league or division filter via `-o/--filter`.

Standings categories:

* all
* division [default]
* conference
* wildcard
* league
* postseason
* preseason

By default, the division standings are displayed for today's date. 
You can add the `-d/--date yyyy-mm-dd` option to show standings for any given date.

You don't have to specify the full standings category, it will match any substring given. e.g. `--standings d`
will match division or `--standings wild` will match wildcard.

You can also use the `-o/--filter` option to narrow down what is displayed. e.g. `--standings division --filter ale`


## 11. Examples

Note: the common options have both short and long options. Both are shown in these examples.


### Live Games

    mlbv --team tor               # play the live Jays game. The feed is chosen based on Jays being home vs. away
    mlbv -t tor --feed national   # play live game, choose the national feed
    mlbv -t tor --feed away       # play live game, choose the away feed. If the Jays are the home team this would choose
                                  # the opponent's feed

### Archived Games

    mlbv --yesterday -t tor        # play yesterday's Jays game
    mlbv --date 2018-03-31 -t tor  # watch the Jays beat the Yankees #spoiler


### Highlights

Use the `--feed` option to select the highlight feed (`recap` or `condensed`):

    mlbv --yesterday -t tor --feed condensed  # condensed feed
    mlbv --yesterday -t tor -f recap          # recap feed

You can also use the `--recaps` option to show highlights for games on given day.
This will show all chosen recaps, one-by-one until finished. A highlight reel.

    mlbv --yesterday --recaps all         # show all available recaps for yesterday games
    mlbv --yesterday --recaps --filter    # show recaps for favourites
    mlbv --yesterday --recaps tor,wsh,bos # show recaps for given set of teams
    mlbv --yesterday --recaps --fetch     # fetch all recaps

### Fetch

In these examples the game is saved to a file (.ts or .mp4) in the current directory.

    mlbv --team tor --fetch
    mlbv --yesterday -t tor -f recap --fetch   # fetch yesterday's recap

### Using `--days` for Schedule View

    mlbv --days 7           # show schedule for upcoming week
    mlbv --days 7 --filter  # show schedule for upcoming week, filtered on favourite teams (from config file)
    mlbv --days 7 --filter --favs 'tor,wsh' # show schedule filtered on favourite teams (from option)

### Linescores

    mlbv -l        # show linescores for today
    mlbv --yes -l  # show linescores for yesterday
    mlbv --date 2018-03-29 --linescore --days 7 --filter  # show linescores for favs in week 1

### Standings

    mlbv --standings             # display division standings
    mlbv --standings division    # display division standings
    mlbv --standings div -o ale  # display AL East division standings
    mlbv --standings league      # display overall league standings
    mlbv --standings all         # display all regular season standings categories

    mlbv --standings --date 2015-10-01  # display division standings for Oct 1, 2015

