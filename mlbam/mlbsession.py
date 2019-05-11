"""
"""
import datetime
import io
import logging
import os
import re
import time

import lxml
import lxml.etree

import mlbam.common.config as config
import mlbam.common.util as util
import mlbam.common.session as session


LOG = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:56.0) Gecko/20100101 Firefox/56.0.4"
PLATFORM = "macintosh"
BAM_SDK_VERSION = "3.0"

API_KEY_URL = "https://www.mlb.com/tv/g490865/"
ACCESS_TOKEN_URL = "https://edge.bamgrid.com/token"
TOKEN_URL_TEMPLATE = "https://media-entitlement.mlb.com/jwt?ipid={ipid}&fingerprint={fingerprint}==&os={platform}&appname=mlbtv_web"

API_KEY_RE = re.compile(r'"apiKey":"([^"]+)"')
CLIENT_API_KEY_RE = re.compile(r'"clientApiKey":"([^"]+)"')

GAME_CONTENT_URL_TEMPLATE = "http://statsapi.mlb.com/api/v1/game/{game_id}/content"

# GAME_FEED_URL = "http://statsapi.mlb.com/api/v1/game/{game_id}/feed/live"

SCHEDULE_TEMPLATE = (
    "http://statsapi.mlb.com/api/v1/schedule?sportId={sport_id}&startDate={start}&endDate={end}"
    "&gameType={game_type}&gamePk={game_id}&teamId={team_id}"
    "&hydrate=linescore,team,game(content(summary,media(epg)),tickets)"
)

STREAM_URL_TEMPLATE = "https://edge.svcs.mlb.com/media/{media_id}/scenarios/browser"


class MLBSession(session.Session):

    def __init__(self):
        session.Session.__init__(self, USER_AGENT, TOKEN_URL_TEMPLATE, PLATFORM)

    def login(self):
        if self.is_logged_in():
            LOG.debug("already logged in")
            return

        initial_url = "https://secure.mlb.com/enterworkflow.do?flowId=registration.wizard&c_id=mlb"
        # res = self.session.get(initial_url)
        # if not res.status_code == 200:
        #     raise SessionException(res.content)
        data = {
            "uri": "/account/login_register.jsp",
            "registrationAction": "identify",
            "emailAddress": config.CONFIG.parser['username'],
            "password": config.CONFIG.parser['password'],
            "submitButton": ""
        }
        LOG.info("Logging in")

        # resp =
        self.session.post("https://securea.mlb.com/authenticate.do",
                          data=data,
                          headers={"Referer": initial_url})

    def is_logged_in(self):
        logged_in_url = "https://web-secure.mlb.com/enterworkflow.do?flowId=registration.newsletter&c_id=mlb"
        content = self.session.get(logged_in_url).text
        parser = lxml.etree.HTMLParser()
        data = lxml.etree.parse(io.StringIO(content), parser)
        if "Login/Register" in data.xpath(".//title")[0].text:
            return False
        return True

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
                raise session.SessionException('update_api_keys: failed to update ' + key)
        self.save()

    def get_access_token(self):
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
        if "errors" in stream and stream["errors"]:
            LOG.error("Could not load stream\n%s", stream)
            return None
        stream_url = stream['stream']['complete']
        return stream_url
