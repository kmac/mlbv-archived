import logging
import os
import requests
import sys
import time


from datetime import datetime
from datetime import timedelta

import mlbam.auth as auth
import mlbam.util as util
import mlbam.config as config


LOG = logging.getLogger(__name__)


def mlb_login():
    """Authenticates user to mlb site."""

    raise Exception("Not implemented")

    url = 'https://user.svc.nhl.com/oauth/token?grant_type=client_credentials'
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "Accept-Language": "en-US,en;q=0.8",
        "User-Agent": config.CONFIG.ua_pc,
        "Origin": "https://www.nhl.com",
        "Authorization": "Basic d2ViX25obC12MS4wLjA6MmQxZDg0NmVhM2IxOTRhMThlZjQwYWM5ZmJjZTk3ZTM=",
    }
    userid = config.CONFIG.parser['username']
    passwd = config.CONFIG.parser['password']
    use_rogers = config.CONFIG.parser.getboolean('use_rogers', False)
    util.log_http(url, 'post', headers, sys._getframe().f_code.co_name)
    r = requests.post(url, headers=headers, data='', cookies=auth.load_cookies(), verify=config.VERIFY_SSL)
    if r.status_code >= 400:
        util.die("Authorization cookie couldn't be downloaded.")

    json_source = r.json()

    if auth.get_auth_cookie() is not None:
        LOG.debug('login: already logged in (we have a valid cookie)')
        return

    auth_cookie = json_source['access_token']

    if use_rogers:
        LOG.info("Logging in via Rogers")
        url = 'https://activation-rogers.svc.nhl.com/ws/subscription/flow/rogers.login'
        login_data = '{"rogerCredentials":{"email":%s,"password":%s}}' % (userid, passwd)
        # referer = "https://www.nhl.com/login/rogers"
    else:
        LOG.info("Logging in via NHL")
        url = 'https://user.svc.nhl.com/v2/user/identity'
        login_data = '{"email":{"address":%s},"type":"email-password","password":{"value":%s}}' % (userid, passwd)

    headers = {
         "Accept": "*/*",
         "Accept-Encoding": "identity",
         "Accept-Language": "en-US,en;q=0.8",
         "Content-Type": "application/json",
         "Authorization": auth_cookie,
         "Connection": "keep-alive",
         "User-Agent": config.CONFIG.ua_pc
    }

    util.log_http(url, 'post', headers, sys._getframe().f_code.co_name)
    r = requests.post(url, headers=headers, data=login_data, cookies=auth.load_cookies(), verify=config.VERIFY_SSL)
    if r.status_code >= 400:
        try:
            json_source = r.json()
            msg = json_source['message']
        except Exception as e:
            msg = "Please check that your username and password are correct"
        LOG.debug('Login Error: json_source: {}'.format(json_source))
        util.die('Login Error: {}'.format(msg))

    LOG.debug('Login successful')
    auth.save_cookies(r.cookies)


def update_session_key(session_key):
    # save session_key to file
    session_key_file = os.path.join(config.CONFIG.dir, 'sessionkey')
    with open(session_key_file, 'w') as f:
        print(session_key, file=f)


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
    r = requests.get(url, headers=headers, cookies=auth.load_cookies(), verify=config.VERIFY_SSL)
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
