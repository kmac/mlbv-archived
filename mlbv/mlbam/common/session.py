"""
This is shamelessly taken from mlbstreamer https://github.com/tonycpsu/mlbstreamer
because I didn't want to reinvent the login/auth/cookie management
(code is modified somewhat arbitrarily. Changed to reduce some imports, and some just to simplify for my own understanding.)
Thanks tonycpsu!

"""
import abc
import datetime
import json
import logging
import os
import requests
import time
import http.cookiejar

import dateutil.parser

import mlbv.mlbam.common.config as config
import mlbv.mlbam.common.util as util


LOG = logging.getLogger(__name__)

SESSION_FILE = os.path.join(config.CONFIG.dir, "session")
COOKIE_FILE = os.path.join(config.CONFIG.dir, 'cookies')


class SessionException(Exception):
    pass


class Session(object):

    def __init__(self, user_agent, token_url_template, platform):
        self.user_agent = user_agent
        self.token_url_template = token_url_template
        self.platform = platform

        self.session = requests.Session()
        self.session.cookies = http.cookiejar.LWPCookieJar()
        if not os.path.exists(COOKIE_FILE):
            self.session.cookies.save(COOKIE_FILE)
        self.session.cookies.load(COOKIE_FILE, ignore_discard=True)
        self.session.headers = {"User-agent": user_agent}
        if os.path.exists(SESSION_FILE):
            self.load()
        else:
            self._state = {
                'api_key': None,
                'client_api_key': None,
                'token': None,
                'access_token': None,
                'access_token_expiry': None
            }
        self.login()

    def __getattr__(self, attr):
        if attr in ["delete", "get", "head", "options", "post", "put", "patch"]:
            return getattr(self.session, attr)
        raise AttributeError(attr)

    def destroy(self):
        if os.path.exists(COOKIE_FILE):
            os.remove(COOKIE_FILE)
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)

    def load(self):
        with open(SESSION_FILE) as infile:
            self._state = json.load(infile)

    def save(self):
        with open(SESSION_FILE, 'w') as outfile:
            json.dump(self._state, outfile)
        self.session.cookies.save(COOKIE_FILE)

    @abc.abstractmethod
    def login(self):
        return

    @abc.abstractmethod
    def is_logged_in(self):
        return False

    def get_cookie_dict(self):
        return requests.utils.dict_from_cookiejar(self.session.cookies)

    def get_cookie(self, name):
        return self.get_cookie_dict().get(name)

    @property
    def ipid(self):
        return self.get_cookie('ipid')

    @property
    def fingerprint(self):
        return self.get_cookie('fprt')

    @property
    def api_key(self):
        if self._state['api_key'] is None:
            self.update_api_keys()
        return self._state['api_key']

    @property
    def client_api_key(self):
        if self._state['client_api_key'] is None:
            self.update_api_keys()
        return self._state['client_api_key']

    @abc.abstractmethod
    def update_api_keys(self):
        return

    @property
    def token(self):
        LOG.debug("getting token")
        if self._state['token'] is None:
            headers = {"x-api-key": self.api_key}
            response = self.session.get(self.token_url_template.format(ipid=self.ipid,
                                                                       fingerprint=self.fingerprint,
                                                                       platform=self.platform),
                                        headers=headers)
            self._state['token'] = response.text
        return self._state['token']

    @token.setter
    def token(self, value):
        self._state['token'] = value

    @property
    def access_token_expiry(self):
        if self._state['access_token_expiry'] is not None:
            return dateutil.parser.parse(str(self._state['access_token_expiry']))
        return None

    @access_token_expiry.setter
    def access_token_expiry(self, val):
        if val:
            self._state['access_token_expiry'] = val.isoformat()

    @property
    def access_token(self):
        LOG.debug("getting access token")
        if not self._state['access_token'] or not self.access_token_expiry or \
                self.access_token_expiry < datetime.datetime.now(tz=datetime.timezone.utc):
            try:
                self._state['access_token'], self.access_token_expiry = self.get_access_token()
            except requests.exceptions.HTTPError:
                # Clear token and then try to get a new access_token
                self.token = None
                self._state['access_token'], self.access_token_expiry = self.get_access_token()
            self.save()
            LOG.debug("access_token: %s", self._state['access_token'])
        return self._state['access_token']

    @abc.abstractmethod
    def get_access_token(self):
        return None

    @abc.abstractmethod
    def lookup_stream_url(self, game_pk, media_id):
        return None

    def save_playlist_to_file(self, stream_url):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Accept-Language": "en-US,en;q=0.8",
            "Connection": "keep-alive",
            "User-Agent": self.user_agent,
            "Cookie": self.access_token
        }
        # util.log_http(stream_url, 'get', headers, sys._getframe().f_code.co_name)
        resp = self.session.get(stream_url, headers=headers)
        playlist = resp.text
        playlist_file = os.path.join(util.get_tempdir(), 'playlist-{}.m3u8'.format(time.strftime("%Y-%m-%d")))
        LOG.info('Writing playlist to: %s', playlist_file)
        with open(playlist_file, 'w') as outf:
            outf.write(playlist)
        LOG.debug('save_playlist_to_file: %s', playlist)
