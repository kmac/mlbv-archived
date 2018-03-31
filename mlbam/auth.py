import logging
import os
import requests
import re
import sys
import time

import lxml
import lxml.etree

import http.cookiejar

from datetime import datetime
from datetime import timedelta

import mlbam.util as util
import mlbam.config as config


LOG = logging.getLogger(__name__)

BAM_SDK_VERSION="3.0"
ACCESS_TOKEN_URL = "https://edge.bamgrid.com/token"
API_KEY_URL= "https://www.mlb.com/tv/g490865/"
API_KEY_RE = re.compile(r'"apiKey":"([^"]+)"')
CLIENT_API_KEY_RE = re.compile(r'"clientApiKey":"([^"]+)"')

API_KEY = 'arBv5yTc359fDsqKdhYC41NZnIFZqEkY5Wyyn9uA'
CLIENT_API_KEY = 'bWxidHYmYnJvd3NlciYxLjAuMA.VfmGMGituFykTR89LFD-Gr5G-lwJ9QbHfXXNBMkuM9M'


def get_cookie_file():
    return os.path.join(config.CONFIG.dir, 'cookies.lwp')


def load_cookies():
    """Load cookies from file."""
    cookie_file = get_cookie_file()
    cj = http.cookiejar.LWPCookieJar()
    if os.path.exists(cookie_file):
        LOG.debug('Loading cookies from {}'.format(cookie_file))
        cj.load(cookie_file, ignore_discard=True)
    return cj


def save_cookies(cookiejar):
    """Save cookies to file."""
    LOG.debug('Saving cookies')
    cookie_file = get_cookie_file()
    cj = http.cookiejar.LWPCookieJar()
    if os.path.exists(cookie_file):
        cj.load(cookie_file, ignore_discard=True)
    for c in cookiejar:
        args = dict(list(vars(c).items()))
        args['rest'] = args['_rest']
        del args['_rest']
        c = http.cookiejar.Cookie(**args)
        cj.set_cookie(c)
    cj.save(cookie_file, ignore_discard=True)


def get_auth_cookie():
    """Get authentication cookie from file."""
    auth_cookie = None
    cj = load_cookies()
    for cookie in cj:
        if cookie.name == "Authorization" and not cookie.is_expired():
            auth_cookie = cookie.value
    return auth_cookie


def update_session_key(session_key):
    # save session_key to file
    session_key_file = os.path.join(config.CONFIG.dir, 'sessionkey')
    with open(session_key_file, 'w') as f:
        print(session_key, file=f)


def find_text_in_str(source, start_str, end_str):
    """taken from plugin.video.mlbtv"""
    start = source.find(start_str)
    end = source.find(end_str, start + len(start_str))
    if start != -1:
        return source[start + len(start_str):end]
    else:
        return ''


def login():
    """
    taken from plugin.video.mlbtv
    """
    url = 'https://secure.mlb.com/pubajaxws/services/IdentityPointService'
    headers = {
        "SOAPAction": "http://services.bamnetworks.com/registration/identityPoint/identify",
        "Content-type": "text/xml; charset=utf-8",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 6.0.1; Hub Build/MHC19J)",
        "Connection": "Keep-Alive"
    }

    payload = "<?xml version='1.0' encoding='UTF-8'?"
    payload += '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    payload += '<SOAP-ENV:Body><tns:identityPoint_identify_request xmlns:tns="http://services.bamnetworks.com/registration/types/1.4">'
    payload += '<tns:identification type="email-password"><tns:id xsi:nil="true"/>'
    payload += '<tns:fingerprint xsi:nil="true"/>'
    payload += '<tns:email>'
    payload += '<tns:id xsi:nil="true"/>'
    payload += '<tns:address>{}</tns:address>'.format(config.CONFIG.parser['username'])
    payload += '</tns:email>'
    payload += '<tns:password>{}</tns:password>'.format(config.CONFIG.parser['password'])
    payload += '<tns:mobilePhone xsi:nil="true"/>'
    payload += '<tns:profileProperty xsi:nil="true"/>'
    payload += '</tns:identification>'
    payload += '</tns:identityPoint_identify_request>'
    payload += '</SOAP-ENV:Body>'
    payload += '</SOAP-ENV:Envelope>'

    util.log_http(url, 'post', headers, sys._getframe().f_code.co_name)
    req = requests.post(url, headers=headers, data=payload, verify=config.VERIFY_SSL)

    """
    Bad username => <status><code>-1000</code><message> [Invalid credentials for identification] [com.bamnetworks.registration.types.exception.IdentificationException: Account doesn't exits]</message><exceptionClass>com.bamnetworks.registration.types.exception.IdentificationException</exceptionClass><detail type="identityPoint" field="exists" message="false" messageKey="identityPoint.exists" /><detail type="identityPoint" field="email-password" message="identification error on identity point of type email-password" messageKey="identityPoint.email-password" /></status>
    Bad password => <status><code>-1000</code><message> [Invalid credentials for identification] [com.bamnetworks.registration.types.exception.IdentificationException: Invalid Password]</message><exceptionClass>com.bamnetworks.registration.types.exception.IdentificationException</exceptionClass><detail type="identityPoint" field="exists" message="true" messageKey="identityPoint.exists" /><detail type="identityPoint" field="email-password" message="identification error on identity point of type email-password" messageKey="identityPoint.email-password" /></status>
    Good => <status><code>1</code><message>OK</message></status>
    """
    if find_text_in_str(req.text, '<code>', '</code>') != '1':
        LOG.debug('Login Error: r.text: %s', req.text)
        msg = find_text_in_str(req.text, 'com.bamnetworks.registration.types.exception.IdentificationException: ', ']</message>')
        util.die('Login Error: {}'.format(msg))

    LOG.debug('Login successful')
    save_cookies(req.cookies)


# def update_api_keys(self):
#     LOG.debug("updating api keys")
#     content = requests.get("https://www.mlb.com/tv/g490865/").text
#     parser = lxml.etree.HTMLParser()
#     data = lxml.etree.parse(StringIO(content), parser)
# 
#     scripts = data.xpath(".//script")
#     for script in scripts:
#         if script.text and "apiKey" in script.text:
#             self._state.api_key = API_KEY_RE.search(script.text).groups()[0]
#         if script.text and "clientApiKey" in script.text:
#             self._state.client_api_key = CLIENT_API_KEY_RE.search(script.text).groups()[0]
#     self.save()


def get_entitlement_token():
    LOG.debug("getting token")
    headers = {"x-api-key": API_KEY}
    response = requests.get("https://media-entitlement.mlb.com/jwt?ipid={ipid}&fingerprint={fingerprint}==&os={platform}&appname=mlbtv_web"
                            .format(ipid=self.ipid, fingerprint=self.fingerprint, platform=PLATFORM),
                            headers=headers)
    return response.text


def get_access_token():
    headers = {
        "Authorization": "Bearer {}".format(CLIENT_API_KEY),
        "User-agent": config.CONFIG.ua_pc,
        "Accept": "application/vnd.media-service+json; version=1",
        "x-bamsdk-version": BAM_SDK_VERSION,
        "x-bamsdk-platform": config.CONFIG.platform,
        "origin": "https://www.mlb.com"
    }
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "platform": "browser",
        "setCookie": "false",
        "subject_token": get_entitlement_token(),
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt"
    }
    response = requests.post(ACCESS_TOKEN_URL, data=data, headers=headers)
    response.raise_for_status()
    token_response = response.json()

    token_expiry = datetime.datetime.now(tz=pytz.UTC) + \
                   datetime.timedelta(seconds=token_response["expires_in"])

    return token_response["access_token"], token_expiry



def get_session_key(game_pk, event_id, content_id, auth_cookie):
    """ game_pk: game_pk
        event_id: eventId
        content_id: mediaPlaybackId
    """

    raise Exception("Not implemented")

    session_key_file = os.path.join(config.CONFIG.dir, 'sessionkey')
    if os.path.exists(session_key_file):
        if datetime.today() - datetime.fromtimestamp(os.path.getmtime(session_key_file)) < timedelta(days=1):
            with open(session_key_file, 'r') as f:
                for line in f:
                    session_key = line.strip()
                    LOG.debug('Using cached session key: {}'.format(session_key))
                    return session_key
    LOG.debug("Requesting session key")
    epoch_time_now = str(int(round(time.time()*1000)))
    url = 'https://mf.svc.nhl.com/ws/media/mf/v2.4/stream?eventId={}&format=json&platform={}&subject=NHLTV&_={}'
    url = url.format(event_id, config.CONFIG.platform, epoch_time_now)
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "Accept-Language": "en-US,en;q=0.8",
        "Connection": "keep-alive",
        "Authorization": auth_cookie,
        "User-Agent": config.CONFIG.ua_pc,
        "Origin": "https://www.nhl.com",
        "Referer": "https://www.nhl.com/tv/{}/{}/{}".format(game_pk, event_id, content_id)
    }
    util.log_http(url, 'get', headers, sys._getframe().f_code.co_name)
    r = requests.get(url, headers=headers, cookies=load_cookies(), verify=config.VERIFY_SSL)
    json_source = r.json()
    LOG.debug('Session key json: {}'.format(json_source))

    if json_source['status_code'] == 1:
        if json_source['user_verified_event'][0]['user_verified_content'][0]['user_verified_media_item'][0]['blackout_status']['status'] == 'BlackedOutStatus':
            session_key = 'blackout'
            LOG.debug('Event blacked out: {}'.format(json_source['user_verified_event'][0]['user_verified_content'][0]['user_verified_media_item'][0]))
        else:
            session_key = str(json_source['session_key'])
    else:
        msg = json_source['status_message']
        util.die('Could not get session key: {}'.format(msg))

    LOG.debug('Retrieved session key: {}'.format(session_key))
    update_session_key(session_key)
    return session_key
