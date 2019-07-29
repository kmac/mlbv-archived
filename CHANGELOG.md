2019.07.28 v0.0.12 Fixed mlbv
Fixed inning offset for both live and archived games
- Fixes Issue #7
    - If you have 'stream_start_offset_secs' set in your config file you may want to reset it to 0 now,
      since the inning times should now be calculated correctly. Alternatively, set it to something 
      like 10 if you want to come in a little early

2019.05.11 v0.0.11 Trying to make travis/setup.py happy

2019.05.11 v0.0.9 Streaming is broken. Use https://github.com/tonycpsu/streamglob

2018.09.29 v0.0.8 Add support for streamlink_extra_args to add enhancement Issue #22
- setting the following config options will stream the output via http on port 8080:
    - video_player=
    - streamlink_extra_args=--player-external-http,--player-external-http-port,8080

2018.08.19 v0.0.7 Fix Issues #18, #19

2018.08.06 v0.0.6 Fix Issues #14, #16, #17

2018.04.24 v0.0.5 Remove configparser from setup.py since it's in base python

2018.04.24 v0.0.4 Fix for mlbv --init when installed via pip (Issue #13)

2018.04.21 v0.0.3 uploaded to pypi
- this is the first relatively stable release

2018.03.31 Initial release on github

