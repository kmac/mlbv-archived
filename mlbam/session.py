"""
This is shamelessly taken from mlbstreamer https://github.com/tonycpsu/mlbstreamer
because I didn't want to reinvent the login/auth/cookie management
(code is modified somewhat arbitrarily. Changed to reduce some imports, and some just to simplify for my own understanding.)
Thanks tonycpsu!

"""
import datetime
import json
import io
import logging
import os
import re
import time
import http.cookiejar

import lxml
import lxml.etree
import requests

import dateutil.parser

import mlbam.config as config
import mlbam.util as util


LOG = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:56.0) Gecko/20100101 Firefox/56.0.4"
PLATFORM = "macintosh"

BAM_SDK_VERSION = "3.0"

API_KEY_URL = "https://www.mlb.com/tv/g490865/"
API_KEY_RE = re.compile(r'"apiKey":"([^"]+)"')
CLIENT_API_KEY_RE = re.compile(r'"clientApiKey":"([^"]+)"')

TOKEN_URL_TEMPLATE = "https://media-entitlement.mlb.com/jwt?ipid={ipid}&fingerprint={fingerprint}==&os={platform}&appname=mlbtv_web"

GAME_CONTENT_URL_TEMPLATE = "http://statsapi.mlb.com/api/v1/game/{game_id}/content"

# GAME_FEED_URL = "http://statsapi.mlb.com/api/v1/game/{game_id}/feed/live"

SCHEDULE_TEMPLATE = (
    "http://statsapi.mlb.com/api/v1/schedule?sportId={sport_id}&startDate={start}&endDate={end}"
    "&gameType={game_type}&gamePk={game_id}&teamId={team_id}"
    "&hydrate=linescore,team,game(content(summary,media(epg)),tickets)"
)

ACCESS_TOKEN_URL = "https://edge.bamgrid.com/token"

STREAM_URL_TEMPLATE = "https://edge.svcs.mlb.com/media/{media_id}/scenarios/browser"

SESSION_FILE = os.path.join(config.CONFIG.dir, "session")
COOKIE_FILE = os.path.join(config.CONFIG.dir, 'cookies')


class MLBSessionException(Exception):
    pass


class MLBSession(object):

    def __init__(self):
        self.session = requests.Session()
        self.session.cookies = http.cookiejar.LWPCookieJar()
        if not os.path.exists(COOKIE_FILE):
            self.session.cookies.save(COOKIE_FILE)
        self.session.cookies.load(COOKIE_FILE, ignore_discard=True)
        self.session.headers = {"User-agent": USER_AGENT}
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

    def login(self):
        if self.is_logged_in():
            LOG.debug("already logged in")
            return

        initial_url = "https://secure.mlb.com/enterworkflow.do?flowId=registration.wizard&c_id=mlb"
        # res = self.session.get(initial_url)
        # if not res.status_code == 200:
        #     raise MLBSessionException(res.content)
        data = {
            "uri": "/account/login_register.jsp",
            "registrationAction": "identify",
            "emailAddress": config.CONFIG.parser['username'],
            "password": config.CONFIG.parser['password'],
            "submitButton": ""
        }
        LOG.info("Logging in")

        resp = self.session.post("https://securea.mlb.com/authenticate.do",
                                 data=data,
                                 headers={"Referer": initial_url})

        if config.CONFIG.parser.getboolean('debug'):
            LOG.debug('Login response: %s', resp.text)

        if not (self.ipid and self.fingerprint):
            raise MLBSessionException("Couldn't get ipid / fingerprint")

        LOG.debug("Successful login: %s", self.ipid)
        self.save()

    def is_logged_in(self):
        logged_in_url = "https://web-secure.mlb.com/enterworkflow.do?flowId=registration.newsletter&c_id=mlb"
        content = self.session.get(logged_in_url).text
        parser = lxml.etree.HTMLParser()
        data = lxml.etree.parse(io.StringIO(content), parser)
        if "Login/Register" in data.xpath(".//title")[0].text:
            return False
        return True

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

    def update_api_keys(self):
        LOG.debug("updating api keys")
        content = self.session.get("https://www.mlb.com/tv/g490865/").text
        parser = lxml.etree.HTMLParser()
        data = lxml.etree.parse(io.StringIO(content), parser)
        scripts = data.xpath(".//script")
        for script in scripts:
            if script.text and 'apiKey' in script.text:
                self._state['api_key'] = API_KEY_RE.search(script.text).groups()[0]
            if script.text and 'clientApiKey' in script.text:
                self._state['client_api_key'] = CLIENT_API_KEY_RE.search(script.text).groups()[0]
        # validate that we updated the keys:
        for key in ('api_key', 'client_api_key'):
            if self._state[key] is None:
                raise MLBSessionException('update_api_keys: failed to update ' + key)
        self.save()

    @property
    def token(self):
        LOG.debug("getting token")
        if self._state['token'] is None:
            headers = {"x-api-key": self.api_key}
            response = self.session.get(TOKEN_URL_TEMPLATE.format(ipid=self.ipid,
                                                                  fingerprint=self.fingerprint,
                                                                  platform=PLATFORM),
                                        headers=headers)
            self._state['token'] = response.text
        return self._state['token']

    @token.setter
    def token(self, value):
        self._state['token'] = value

    @property
    def access_token_expiry(self):
        if self._state['access_token_expiry'] is not None:
            return dateutil.parser.parse(self._state['access_token_expiry'])
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
                self._state['access_token'], self.access_token_expiry = self._get_access_token()
            except requests.exceptions.HTTPError:
                # Clear token and then try to get a new access_token
                self.token = None
                self._state['access_token'], self.access_token_expiry = self._get_access_token()
            self.save()
            LOG.debug("access_token: %s", self._state['access_token'])
        return self._state['access_token']

    def _get_access_token(self):
        headers = {
            "Authorization": "Bearer %s" % (self.client_api_key),
            "User-agent": USER_AGENT,
            "Accept": "application/vnd.media-service+json; version=1",
            "x-bamsdk-version": BAM_SDK_VERSION,
            "x-bamsdk-platform": PLATFORM,
            "origin": "https://www.mlb.com"
        }
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "platform": "browser",
            "setCookie": "false",
            "subject_token": self.token,
            "subject_token_type": "urn:ietf:params:oauth:token-type:jwt"
        }
        response = self.session.post(ACCESS_TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()
        token_response = response.json()

        token_expiry = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=token_response["expires_in"])

        return token_response["access_token"], token_expiry

    def lookup_stream_url(self, game_pk, media_id):
        """ game_pk: game_pk
            media_id: mediaPlaybackId
        """
        stream_url = None
        headers = {
            "Authorization": self.access_token,
            "User-agent": USER_AGENT,
            "Accept": "application/vnd.media-service+json; version=1",
            "x-bamsdk-version": "3.0",
            "x-bamsdk-platform": PLATFORM,
            "origin": "https://www.mlb.com"
        }
        response = self.session.get(STREAM_URL_TEMPLATE.format(media_id=media_id), headers=headers)
        if response is not None and config.SAVE_JSON_FILE:
            output_filename = 'stream'
            if config.SAVE_JSON_FILE_BY_TIMESTAMP:
                json_file = os.path.join(util.get_tempdir(),
                                         '{}-{}.json'.format(output_filename, time.strftime("%Y-%m-%d-%H%M")))
            else:
                json_file = os.path.join(util.get_tempdir(), '{}.json'.format(output_filename))
            with open(json_file, 'w') as out:  # write date to json_file
                out.write(response.text)

        stream = response.json()
        LOG.debug("lookup_stream_url, stream response: %s", stream)
        if "errors" in stream and len(stream["errors"]):
            LOG.error("Could not load stream\n%s", stream)
            return None
        stream_url = stream['stream']['complete']
        return stream_url

    def save_playlist_to_file(self, stream_url):
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Accept-Language": "en-US,en;q=0.8",
            "Connection": "keep-alive",
            "User-Agent": USER_AGENT,
            "Cookie": self.access_token
        }
        # util.log_http(stream_url, 'get', headers, sys._getframe().f_code.co_name)
        resp = self.session.get(stream_url, headers=headers)
        playlist = resp.text
        playlist_file = os.path.join(util.get_tempdir(), 'playlist-{}.m3u8'.format(time.strftime("%Y-%m-%d")))
        LOG.info('Writing playlist to: {}'.format(playlist_file))
        with open(playlist_file, 'w') as f:
            f.write(playlist)
        LOG.debug('save_playlist_to_file: {}'.format(playlist))
