import http.cookiejar
import logging
import os

import mlbam.config as config


LOG = logging.getLogger(__name__)


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
