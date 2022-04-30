"""
mlbsession
"""
import datetime
import io
import logging
import os
import random
import re
import string

import lxml
import lxml.etree
import pytz

import mlbv.mlbam.common.config as config
import mlbv.mlbam.common.util as util
import mlbv.mlbam.common.session as session

LOG = logging.getLogger(__name__)

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
OKTA_AUTHORIZE_URL = "https://ids.mlb.com/oauth2/aus1m088yK07noBfh356/v1/authorize"
BAM_DEVICES_URL = "https://us.edge.bamgrid.com/devices"
BAM_SESSION_URL = "https://us.edge.bamgrid.com/session"
BAM_TOKEN_URL = "https://us.edge.bamgrid.com/token"
BAM_ENTITLEMENT_URL = "https://media-entitlement.mlb.com/api/v3/jwt"
GAME_CONTENT_URL_TEMPLATE = "http://statsapi.mlb.com/api/v1/game/{game_id}/content"
STREAM_URL_TEMPLATE = (
    "https://edge.svcs.mlb.com/media/{media_id}/scenarios/browser~csai"
)
AIRINGS_URL_TEMPLATE = (
    "https://search-api-mlbtv.mlb.com/svc/search/v2/graphql/persisted/query/"
    "core/Airings?variables={{%22partnerProgramIds%22%3A[%22{game_id}%22]}}"
)


def gen_random_string(n):
    return "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(n)
    )


class SGProviderLoginException(BaseException):
    """Flags that a login is required."""

    pass


# Notes on okta OIDC:
# https://developer.okta.com/blog/2017/07/25/oidc-primer-part-1
#
# Discover endpoints:
# https://ids.mlb.com/oauth2/aus1m088yK07noBfh356/.well-known/openid-configuration
#
class MLBSession(session.Session):
    """MLB Session handling"""

    def __init__(self):
        session.Session.__init__(self, USER_AGENT, PLATFORM)

    # Override
    def login(self):
        """Posts to the AUTHN_URL and saves the session token"""

        authn_params = {
            "username": config.CONFIG.parser["username"],
            "password": config.CONFIG.parser["password"],
            "options": {
                "multiOptionalFactorEnroll": False,
                "warnBeforePasswordExpired": True,
            },
        }
        LOG.debug("login: %s", authn_params["username"])
        authn_response = self.session.post(AUTHN_URL, json=authn_params).json()
        LOG.debug("login: authn_response: %s", authn_response)
        self.session_token = authn_response["sessionToken"]
        self._state["session_token_time"] = str(datetime.datetime.now(tz=pytz.UTC))
        self.save()

    # Override
    def _refresh_access_token(self, clear_token=False):
        """Update API keys"""

        if clear_token:
            self.session_token = None

        LOG.debug("Updating MLB api keys")
        content = self.session.get(MLB_API_KEY_URL).text
        if config.VERBOSE:
            LOG.debug("MLB api keys: %s", content)
        parser = lxml.etree.HTMLParser()
        data = lxml.etree.parse(io.StringIO(content), parser)

        # API key
        scripts = data.xpath(".//script")
        for script in scripts:
            if script.text and "apiKey" in script.text:
                self._state["api_key"] = self.API_KEY_RE.search(script.text).groups()[0]
            if script.text and "clientApiKey" in script.text:
                self._state["client_api_key"] = CLIENT_API_KEY_RE.search(
                    script.text
                ).groups()[0]

        LOG.debug("Updating Okta api keys")
        content = self.session.get(MLB_OKTA_URL).text
        self._state["okta_client_id"] = OKTA_CLIENT_ID_RE.search(content).groups()[0]
        LOG.debug("okta_client_id: %s", self._state["okta_client_id"])

        # OKTA Token
        def get_okta_token():
            state_param = gen_random_string(64)
            nonce_param = gen_random_string(64)
            authz_params = {
                "client_id": self._state["okta_client_id"],
                "redirect_uri": "https://www.mlb.com/login",
                "response_type": "id_token token",
                "response_mode": "okta_post_message",
                "state": state_param,
                "nonce": nonce_param,
                "prompt": "none",
                "sessionToken": self.session_token,  # may trigger login
                "scope": "openid email",
            }
            authz_response = self.session.get(OKTA_AUTHORIZE_URL, params=authz_params)
            authz_content = authz_response.text
            if config.VERBOSE:
                LOG.debug("get_okta_token reponse: %s", authz_content)
            for line in authz_content.split("\n"):
                if "data.access_token" in line:
                    return line.split("'")[1].encode("utf-8").decode("unicode_escape")
                if "data.error = 'login_required'" in line:
                    raise SGProviderLoginException
            LOG.debug("get_okta_token failed: %s", authz_content)
            raise Exception("could not authenticate: {authz_content}")

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
            "deviceProfile": "macosx",
        }

        devices_response = self.session.post(
            BAM_DEVICES_URL, headers=devices_headers, json=devices_params
        ).json()

        # Issue #53: no assertion key here:
        if "assertion" in devices_response:
            devices_assertion = devices_response["assertion"]
        else:
            devices_assertion = None
            LOG.error("No assertion key in devices response")
            LOG.debug("No assertion key in devices response: %s", devices_response.text)

        # Device token
        token_params = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "latitude": "0",
            "longitude": "0",
            "platform": "browser",
            "subject_token": devices_assertion,
            "subject_token_type": "urn:bamtech:params:oauth:token-type:device",
        }
        token_response = self.session.post(
            BAM_TOKEN_URL, headers=devices_headers, data=token_params
        ).json()

        device_access_token = token_response["access_token"]

        # Create session
        session_headers = {
            "Authorization": device_access_token,
            "User-agent": USER_AGENT,
            "Origin": "https://www.mlb.com",
            "Accept": "application/vnd.session-service+json; version=1",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.5",
            "x-bamsdk-version": BAM_SDK_VERSION,
            "x-bamsdk-platform": PLATFORM,
            "Content-type": "application/json",
            "TE": "Trailers",
        }
        session_response = self.session.get(
            BAM_SESSION_URL, headers=session_headers
        ).json()
        device_id = session_response["device"]["id"]

        # Entitlement token
        entitlement_params = {"os": PLATFORM, "did": device_id, "appname": "mlbtv_web"}

        entitlement_headers = {
            "Authorization": "Bearer %s" % (self._state["OKTA_ACCESS_TOKEN"]),
            "Origin": "https://www.mlb.com",
            # TODO: is api_key correct?  always None?
            "x-api-key": self._state["api_key"],
        }
        entitlement_response = self.session.get(
            BAM_ENTITLEMENT_URL, headers=entitlement_headers, params=entitlement_params
        )

        entitlement_token = entitlement_response.content

        # Get access token
        headers = {
            "Authorization": "Bearer %s" % self._state["client_api_key"],
            "User-agent": USER_AGENT,
            "Accept": "application/vnd.media-service+json; version=1",
            "x-bamsdk-version": BAM_SDK_VERSION,
            "x-bamsdk-platform": PLATFORM,
            "origin": "https://www.mlb.com",
        }
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "platform": "browser",
            "subject_token": entitlement_token,
            "subject_token_type": "urn:bamtech:params:oauth:token-type:account",
        }
        response = self.session.post(BAM_TOKEN_URL, data=data, headers=headers)
        # from requests_toolbelt.utils import dump
        # print(dump.dump_all(response).decode("utf-8"))
        response.raise_for_status()
        token_response = response.json()
        if config.VERBOSE:
            LOG.debug("token_response: %s", token_response)

        # Finally: update the token and expiry in our _state:
        self._state["access_token_expiry"] = str(
            datetime.datetime.now(tz=pytz.UTC)
            + datetime.timedelta(seconds=token_response["expires_in"])
        )
        self._state["access_token"] = token_response["access_token"]
        self.save()

    # Override
    def lookup_stream_url(self, game_pk, media_id):
        """game_pk: game_pk
        media_id: mediaPlaybackId
        """
        stream_url = None
        headers = {
            "Authorization": self.access_token,
            "User-agent": USER_AGENT,
            "Accept": "application/vnd.media-service+json; version=1",
            "x-bamsdk-version": BAM_SDK_VERSION,
            "x-bamsdk-platform": PLATFORM,
            "origin": "https://www.mlb.com",
        }
        response = self.session.get(
            STREAM_URL_TEMPLATE.format(media_id=media_id), headers=headers
        )
        if response is not None and config.SAVE_JSON_FILE:
            output_filename = "stream"
            json_file = os.path.join(
                util.get_tempdir(), "{}.json".format(output_filename)
            )
            with open(json_file, "w") as out:  # write date to json_file
                out.write(response.text)

        stream = response.json()
        LOG.debug("lookup_stream_url, stream response: %s", stream)
        if "errors" in stream and stream["errors"]:
            LOG.error("Could not load stream\n%s", stream)
            return None
        stream_url = stream["stream"]["complete"]
        return stream_url
