"""
Utility functions
"""

import logging
import os.path
import shutil
import sys
import tempfile
import time

import textwrap

from datetime import datetime
from datetime import timezone
from dateutil import tz
from html.parser import HTMLParser

import mlbv.mlbam.common.config as config


LOG = None


class Usage(Exception):
    def __init__(self, msg='', include_doc=False):
        if msg is None:
            msg = ''
        self.msg = msg
        if include_doc:
            self.msg += '\n' + __doc__ % (sys.argv[0], )


def init_logging(log_file=None, append=False, console_loglevel=logging.INFO):
    """Set up logging to file and console."""
    if log_file is not None:
        if append:
            filemode_val = 'a'
        else:
            filemode_val = 'w'
        logging.basicConfig(level=logging.DEBUG,
                            format="%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s",
                            # datefmt='%m-%d %H:%M',
                            filename=log_file,
                            filemode=filemode_val)
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(console_loglevel)
    # set a format which is simpler for console use
    formatter = logging.Formatter("%(message)s")
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)
    global LOG
    LOG = logging.getLogger(__name__)


def die(msg, exit_code=1):
    """Logs error message then exits with code."""
    if LOG is not None:
        LOG.error("FATAL: " + msg)
    else:
        print("FATAL: " + msg)
    sys.exit(exit_code)


def get_tempdir():
    """Create a directory for ourselves in the system tempdir."""
    tempdir = config.CONFIG.parser.get('tempdir', None)
    if tempdir:
        if '<timestamp>' in tempdir:
            tempdir = tempdir.replace('<timestamp>', time.strftime('%Y-%m-%d-%H%M'))
    else:
        script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        tempdir = os.path.join(tempfile.gettempdir(), script_name)
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    return tempdir


def convert_time_to_local(d):
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    utc = d.replace(tzinfo=from_zone)
    if config.CONFIG.parser['timeformat'] == '12H':
        return utc.astimezone(to_zone).strftime('%I:%M %p').replace('PM', 'pm').replace('AM', 'am')
    return utc.astimezone(to_zone).strftime('%H:%M')


def has_reached_time(datetime_val_utc):
    # return datetime_val_utc.replace(timezone.utc) < datetime.now(timezone.utc)
    return datetime_val_utc < datetime.now(timezone.utc)


def get_csv_list(csv_string):
    """Returns a normalized list from a csv string."""
    return [l.strip() for l in csv_string.split(',')]


def substring_match(input_option, full_option):
    """Tests if the full_option string matches the input_option string.
    Where input_option can be a substring of the full_option, it is considered a match.
    full_option can also be a list.
    """
    if isinstance(full_option, (list, tuple)):
        for fullopt in full_option:
            if substring_match(input_option, fullopt):
                return True
        return None
    num_chars = len(input_option)
    return input_option[:num_chars] == full_option[:num_chars]


def expand_substring_match(input_option, full_option):
    """Tests if the full_option string matches the input_option string.
    Where input_option can be a substring of the full_option, it is considered a match.
    Returns the expanded full_option value, or None
    """
    if isinstance(full_option, (list, tuple)):
        for fullopt in full_option:
            if substring_match(input_option, fullopt):
                return fullopt
        return None
    if substring_match(input_option, full_option):
        return full_option
    return None


def log_http(url, request_type=None, headers=None, method_name=None):
    """Helper function to log http requests."""
    msg = ''
    if method_name is not None:
        msg += '{}: '.format(method_name)
    if request_type is not None:
        msg += "HTTP '{}' request: {}".format(request_type.upper(), url)
    else:
        msg += "HTTP request: {}".format(url)
    if headers is not None:
        msg += ', headers:{}'.format(headers)
    LOG.debug(msg)


class HTMLStripper(HTMLParser):
    """Modified from https://stackoverflow.com/a/11063816
    https://docs.python.org/3.7/library/html.parser.html?highlight=htmlparser
    """
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                self.fed.append(str(attr[1] + ' '))

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self, wrap=True):
        if wrap:
            terminal_size = shutil.get_terminal_size((80, 40))
            wrap_columns = terminal_size.columns
            if wrap_columns > int(config.CONFIG.parser['info_display_max_columns']):
                wrap_columns = int(config.CONFIG.parser['info_display_max_columns'])
            return '\n'.join([textwrap.fill(x, wrap_columns) for x in ''.join(self.fed).split('\n')])
        return ''.join(self.fed)


def strip_html_tags(htmltext, wrap=True):
    stripper = HTMLStripper()
    stripper.feed(htmltext)
    return stripper.get_data(wrap)


# # https://stackoverflow.com/a/7778368
# import html.parser
# class HTMLTextExtractor(html.parser.HTMLParser):
#     def __init__(self):
#         super(HTMLTextExtractor, self).__init__()
#         self.result = [ ]
# 
#     def handle_data(self, d):
#         self.result.append(d)
# 
#     def get_text(self):
#         return ''.join(self.result)
# 
# def html_to_text(html):
#     """Converts HTML to plain text (stripping tags and converting entities).
#     >>> html_to_text('<a href="#">Demo<!--...--> <em>(&not; \u0394&#x03b7;&#956;&#x03CE;)</em></a>')
#     'Demo (\xac \u0394\u03b7\u03bc\u03ce)'
# 
#     "Plain text" doesn't mean result can safely be used as-is in HTML.
#     >>> html_to_text('&lt;script&gt;alert("Hello");&lt;/script&gt;')
#     '<script>alert("Hello");</script>'
# 
#     Always use html.escape to sanitize text before using in an HTML context!
# 
#     HTMLParser will do its best to make sense of invalid HTML.
#     >>> html_to_text('x < y &lt z <!--b')
#     'x < y < z '
# 
#     Unrecognized named entities are included as-is. '&apos;' is recognized,
#     despite being XML only.
#     >>> html_to_text('&nosuchentity; &apos; ')
#     "&nosuchentity; ' "
#     """
#     s = HTMLTextExtractor()
#     s.feed(html)
#     return s.get_text()
