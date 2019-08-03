"""
"""
import datetime
import io
import logging
import os
import random
import re
import string
import time

import lxml
import lxml.etree
import pytz
import requests

import mlbv.mlbam.common.config as config
import mlbv.mlbam.common.util as util
import mlbv.mlbam.common.session as session

LOG = logging.getLogger(__name__)

# USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:56.0) Gecko/20100101 Firefox/56.0.4"
# PLATFORM = "macintosh"
# BAM_SDK_VERSION = "3.4"
#
# AUTHN_URL = "https://ids.mlb.com/api/v1/authn"
# AUTHZ_URL = "https://ids.mlb.com/oauth2/aus1m088yK07noBfh356/v1/authorize"
#
# API_KEY_URL = "https://www.mlb.com/tv/g490865/"
ACCESS_TOKEN_URL = "https://us.edge.bamgrid.com/token"
# BAM_DEVICES_URL = "https://us.edge.bamgrid.com/devices"
TOKEN_URL_TEMPLATE = "https://media-entitlement.mlb.com/jwt?ipid={ipid}&fingerprint={fingerprint}==&os={platform}&appname=mlbtv_web"
#
# MLB_OKTA_URL = "https://www.mlbstatic.com/mlb.com/vendor/mlb-okta/mlb-okta.js"
# OKTA_CLIENT_ID_RE = re.compile("""production:{clientId:"([^"]+)",""")
#
# API_KEY_RE = re.compile(r'"apiKey":"([^"]+)"')
# CLIENT_API_KEY_RE = re.compile(r'"clientApiKey":"([^"]+)"')
#
# GAME_CONTENT_URL_TEMPLATE = "http://statsapi.mlb.com/api/v1/game/{game_id}/content"
#
#
#
# # GAME_FEED_URL = "http://statsapi.mlb.com/api/v1/game/{game_id}/feed/live"
#
# SCHEDULE_TEMPLATE = (
#     "http://statsapi.mlb.com/api/v1/schedule?sportId={sport_id}&startDate={start}&endDate={end}"
#     "&gameType={game_type}&gamePk={game_id}&teamId={team_id}"
#     "&hydrate=linescore,team,game(content(summary,media(epg)),tickets)"
# )
#
# STREAM_URL_TEMPLATE = "https://edge.svcs.mlb.com/media/{media_id}/scenarios/browser~csai"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:66.0) "
    "Gecko/20100101 Firefox/66.0"
)

PLATFORM = "macintosh"

BAM_SDK_VERSION = "3.4"

MLB_API_KEY_URL = "https://www.mlb.com/tv/g490865/"

API_KEY_RE = re.compile(r'"apiKey":"([^"]+)"')

CLIENT_API_KEY_RE = re.compile(r'"clientApiKey":"([^"]+)"')

OKTA_CLIENT_ID_RE = re.compile("""production:{clientId:"([^"]+)",""")

MLB_OKTA_URL = "https://www.mlbstatic.com/mlb.com/vendor/mlb-okta/mlb-okta.js"

AUTHN_URL = "https://ids.mlb.com/api/v1/authn"

AUTHZ_URL = "https://ids.mlb.com/oauth2/aus1m088yK07noBfh356/v1/authorize"

BAM_DEVICES_URL = "https://us.edge.bamgrid.com/devices"

BAM_SESSION_URL = "https://us.edge.bamgrid.com/session"

BAM_TOKEN_URL = "https://us.edge.bamgrid.com/token"

BAM_ENTITLEMENT_URL = "https://media-entitlement.mlb.com/api/v3/jwt"

GAME_CONTENT_URL_TEMPLATE="http://statsapi.mlb.com/api/v1/game/{game_id}/content"

STREAM_URL_TEMPLATE="https://edge.svcs.mlb.com/media/{media_id}/scenarios/browser~csai"

AIRINGS_URL_TEMPLATE=(
    "https://search-api-mlbtv.mlb.com/svc/search/v2/graphql/persisted/query/"
    "core/Airings?variables={{%22partnerProgramIds%22%3A[%22{game_id}%22]}}"
)


def gen_random_string(n):
    return ''.join(
        random.choice(
            string.ascii_uppercase + string.digits
        ) for _ in range(n)
    )


class SGProviderLoginException(BaseException):
    pass


class MLBSession(session.Session):

    def __init__(self):
        session.Session.__init__(self, USER_AGENT, TOKEN_URL_TEMPLATE, PLATFORM)

    def login(self):

        authn_params = {
            "username": config.CONFIG.parser['username'],
            "password": config.CONFIG.parser['password'],
            "options": {
                "multiOptionalFactorEnroll": False,
                "warnBeforePasswordExpired": True
            }
        }
        authn_response = self.post(AUTHN_URL, json=authn_params).json()
        self._state["session_token"] = authn_response["sessionToken"]

        # logger.debug("logged in: %s" %(self.ipid))
        self.save()

    def is_logged_in(self):
        logged_in_url = "https://secure.mlb.com/account/login_register.jsp?flowId=registration.newsletter&c_id=mlb"
        content = self.session.get(logged_in_url).text
        parser = lxml.etree.HTMLParser()
        data = lxml.etree.parse(io.StringIO(content), parser)
        if "Login/Register" in data.xpath(".//title")[0].text:
            return False
        return True

    def update_api_keys(self):

        LOG.debug("updating MLB api keys")
        content = self.get(MLB_API_KEY_URL).text
        parser = lxml.etree.HTMLParser()
        data = lxml.etree.parse(io.StringIO(content), parser)

        # API key

        scripts = data.xpath(".//script")
        for script in scripts:
            if script.text and "apiKey" in script.text:
                self._state.api_key = self.API_KEY_RE.search(script.text).groups()[0]
            if script.text and "clientApiKey" in script.text:
                self._state["client_api_key"] = CLIENT_API_KEY_RE.search(script.text).groups()[0]

        LOG.debug("updating Okta api keys")
        content = self.get(MLB_OKTA_URL).text
        self._state["okta_client_id"] = OKTA_CLIENT_ID_RE.search(content).groups()[0]

        # OKTA Token

        def get_okta_token():

            STATE = gen_random_string(64)
            NONCE = gen_random_string(64)

            AUTHZ_PARAMS = {
                "client_id": self._state["okta_client_id"],
                "redirect_uri": "https://www.mlb.com/login",
                "response_type": "id_token token",
                "response_mode": "okta_post_message",
                "state": STATE,
                "nonce": NONCE,
                "prompt": "none",
                "sessionToken": self._state["session_token"],
                "scope": "openid email"
            }
            authz_response = self.get(AUTHZ_URL, params=AUTHZ_PARAMS)
            authz_content = authz_response.text
            for line in authz_content.split("\n"):
                if "data.access_token" in line:
                    return line.split("'")[1].encode('utf-8').decode('unicode_escape')
                elif "data.error = 'login_required'" in line:
                    raise SGProviderLoginException
            raise Exception("could not authenticate: {authz_contet}")

        try:
            self._state["OKTA_ACCESS_TOKEN"] = get_okta_token()
        except SGProviderLoginException:
            # not logged in -- get session token and try again
            self.login()
            self._state["OKTA_ACCESS_TOKEN"] = get_okta_token()

        assert self._state["OKTA_ACCESS_TOKEN"] is not None

        # Device Assertion

        devices_headers = {
            "Authorization": "Bearer %s" % (self.client_api_key),
            "Origin": "https://www.mlb.com",
        }

        devices_params = {
            "applicationRuntime": "firefox",
            "attributes": {},
            "deviceFamily": "browser",
            "deviceProfile": "macosx"
        }

        devices_response = self.post(
            BAM_DEVICES_URL,
            headers=devices_headers, json=devices_params
        ).json()

        DEVICES_ASSERTION = devices_response["assertion"]

        # Device token

        TOKEN_PARAMS = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "latitude": "0",
            "longitude": "0",
            "platform": "browser",
            "subject_token": DEVICES_ASSERTION,
            "subject_token_type": "urn:bamtech:params:oauth:token-type:device"
        }
        token_response = self.post(
            BAM_TOKEN_URL, headers=devices_headers, data=TOKEN_PARAMS
        ).json()

        DEVICE_ACCESS_TOKEN = token_response["access_token"]
        DEVICE_REFRESH_TOKEN = token_response["refresh_token"]

        # Create session

        SESSION_HEADERS = {
            "Authorization": DEVICE_ACCESS_TOKEN,
            "User-agent": USER_AGENT,
            "Origin": "https://www.mlb.com",
            "Accept": "application/vnd.session-service+json; version=1",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.5",
            "x-bamsdk-version": BAM_SDK_VERSION,
            "x-bamsdk-platform": PLATFORM,
            "Content-type": "application/json",
            "TE": "Trailers"
        }
        session_response = self.get(
            BAM_SESSION_URL,
            headers=SESSION_HEADERS
        ).json()
        DEVICE_ID = session_response["device"]["id"]

        # Entitlement token

        ENTITLEMENT_PARAMS = {
            "os": PLATFORM,
            "did": DEVICE_ID,
            "appname": "mlbtv_web"
        }

        ENTITLEMENT_HEADERS = {
            "Authorization": "Bearer %s" % (self._state["OKTA_ACCESS_TOKEN"]),
            "Origin": "https://www.mlb.com",
            "x-api-key": self._state["api_key"]

        }
        entitlement_response = self.get(
            BAM_ENTITLEMENT_URL,
            headers=ENTITLEMENT_HEADERS,
            params=ENTITLEMENT_PARAMS
        )

        ENTITLEMENT_TOKEN = entitlement_response.content

        # Get access token

        headers = {
            "Authorization": "Bearer %s" % self._state["client_api_key"],
            "User-agent": USER_AGENT,
            "Accept": "application/vnd.media-service+json; version=1",
            "x-bamsdk-version": BAM_SDK_VERSION,
            "x-bamsdk-platform": PLATFORM,
            "origin": "https://www.mlb.com"
        }
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "platform": "browser",
            "subject_token": ENTITLEMENT_TOKEN,
            "subject_token_type": "urn:bamtech:params:oauth:token-type:account"
        }
        response = self.post(
            BAM_TOKEN_URL,
            data=data,
            headers=headers
        )
        # from requests_toolbelt.utils import dump
        # print(dump.dump_all(response).decode("utf-8"))
        response.raise_for_status()
        token_response = response.json()

        self._state["access_token_expiry"] = str(datetime.datetime.now(tz=pytz.UTC) + \
                                             datetime.timedelta(seconds=token_response["expires_in"]))
        self._state["access_token"] = token_response["access_token"]
        self.save()

    def get_access_token(self):

        if not self._state["access_token"] or not self._state["access_token_expiry"] or \
                self.access_token_expiry < datetime.datetime.now(tz=pytz.UTC):
            try:
                self.update_api_keys()
            except requests.exceptions.HTTPError:
                # Clear token and then try to get a new access_token
                self.update_api_keys()

        LOG.debug("access_token: %s" %(self._state["access_token"]))
        return self._state["access_token"], self._state["access_token_expiry"]

    def lookup_stream_url(self, game_pk, media_id):
        """ game_pk: game_pk
            media_id: mediaPlaybackId
        """
        stream_url = None
        self._state["access_token"], self._state["token_expiry"], = self.get_access_token()
        headers = {
            "Authorization": self._state["access_token"],
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
