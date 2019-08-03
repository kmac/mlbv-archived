"""
Utility functions
"""

import logging
import os.path
import sys
import tempfile
import time

import requests

from datetime import datetime
from datetime import timezone
from dateutil import tz

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
    script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    tempdir = os.path.join(tempfile.gettempdir(), script_name)
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    return tempdir


def request_json(url, output_filename=None):
    """Sends a request expecting a json-formatted response."""
    LOG.debug('Getting url=%s ...', url)
    headers = {
        'User-Agent': config.CONFIG.ua_iphone,
        'Connection': 'close'
    }
    log_http(url, 'get', headers, sys._getframe().f_code.co_name)
    response = requests.get(url, headers=headers, verify=config.VERIFY_SSL)
    response.raise_for_status()

    # Note: this fails on windows in some cases https://github.com/kennethreitz/requests-html/issues/171
    if output_filename is not None and config.DEBUG and config.SAVE_JSON_FILE:
        if config.SAVE_JSON_FILE_BY_TIMESTAMP:
            json_file = os.path.join(get_tempdir(),
                                     '{}-{}.json'.format(output_filename, time.strftime("%Y-%m-%d-%H%M")))
        else:
            json_file = os.path.join(get_tempdir(), '{}.json'.format(output_filename))
        with open(json_file, 'w', encoding='utf-8') as out:  # write date to json_file
            out.write(response.text)

    return response.json()


def convert_time_to_local(d):
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    utc = d.replace(tzinfo=from_zone)
    return utc.astimezone(to_zone).strftime('%H:%M')


def has_reached_time(datetime_val_utc):
    # return datetime_val_utc.replace(timezone.utc) < datetime.now(timezone.utc)
    return datetime_val_utc < datetime.now(timezone.utc)


def get_csv_list(csv_string):
    """Returns a normalized list from a csv string."""
    return [l.strip() for l in csv_string.split(',')]


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


