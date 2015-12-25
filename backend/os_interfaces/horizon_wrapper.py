# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import http.cookies
import logbook
import posixpath
import requests

import conf
import errors


class HorizonAuth(object):

    def __init__(self, csrftoken='', sessionid=''):
        self.horizon_url = conf.openstack.horizon_url
        self.region = None
        self.session = requests.Session()
        if csrftoken and sessionid:
            self.session.cookies.set(name='sessionid', value=sessionid)
            self.session.cookies.set(name='csrftoken', value=csrftoken)

    def _check_already_logged_in(self, username, relogin=False):
        horizon_dashboard_url = posixpath.join(self.horizon_url, 'project/')
        try:
            # ekosareva: passing cookies as a request param it's workaround. There is bug in requests lib:
            # response's cookie doesn't override session's cookie with the same name, as a result we have
            # 'multiple cookie' CookieConflictError exception.
            init_csrftoken = self.session.cookies.get('csrftoken')
            init_sessionid = self.session.cookies.get('sessionid')
            self.session.cookies.clear()
            logbook.debug("Request project page in horizon for {}. URL: {}", username, horizon_dashboard_url)
            horizon_response = self.session.get(horizon_dashboard_url, verify=False, stream=False,
                                                cookies={'csrftoken': init_csrftoken, 'sessionid': init_sessionid})
        except requests.exceptions.RequestException as e:
            logbook.warning('Request exception happens during getting to Horizon on {} for user "{}": {}',
                            horizon_dashboard_url, username, e)
            raise errors.HorizonRequestError()

        if horizon_response.status_code != 200:
            logbook.warning('Request to {} is not succeed for user "{}": status code = {}',
                            horizon_dashboard_url, username, horizon_response.status_code)
            raise errors.HorizonRequestError()

        if horizon_response.url != horizon_dashboard_url:
            logbook.info("Request was redirected: {}", horizon_response.url)
            self.region = self._get_region(horizon_response.text)
            return False

        if not relogin and self._get_logged_in_username(horizon_response.text) != username:
            self.region = ''
            self.session.cookies.clear()
            logbook.warning('User "{}" has cookies for another user. Perform re-login.', username)
            return self._check_already_logged_in(username, relogin=True)
        return True

    def login_os_user(self, username, password):
        if self._check_already_logged_in(username):
            logbook.info('User "{}" is logged in already and has valid cookies.', username)
            return {}

        horizon_auth_login = posixpath.join(self.horizon_url, 'auth/login/')
        data = {
            'region': self.region,
            'username': username,
            'password': password,
            'csrfmiddlewaretoken': self.session.cookies.get('csrftoken')
        }
        try:
            data_without_password = data.copy()
            data_without_password.pop("password")
            logbook.info("Try authorize in horizon: {}, {}", horizon_auth_login, data_without_password)
            horizon_auth_response = self.session.post(horizon_auth_login, data=data, verify=False, stream=False)
        except requests.exceptions.RequestException as e:
            logbook.warning('Request exception happens during posting data to {} for user "{}": {}',
                            horizon_auth_login, username, e)
            raise errors.HorizonRequestError()

        if horizon_auth_response.status_code != 200 or horizon_auth_response.url == horizon_auth_login:
            logbook.warning('Unable to login into Horizon on {} for login = {} with status = {}: {}. Response url: {}',
                            horizon_auth_login, username, horizon_auth_response.status_code,
                            horizon_auth_response.text, horizon_auth_response.url)
            raise errors.HorizonUnauthorized()
        cookie = horizon_auth_response.headers.get('Set-Cookie')
        logbook.debug("Horizon cookies: {}", cookie)

        return http.cookies.SimpleCookie(cookie)

    @staticmethod
    def _get_region(html):
        soup = BeautifulSoup(html, 'html.parser')
        region_tag = soup.find(id='id_region')
        return region_tag['value'] if region_tag else ''

    @staticmethod
    def _get_logged_in_username(html):
        soup = BeautifulSoup(html, 'html.parser')
        user_name_tag = soup.select('#user_info > #profile_editor_switcher > a > div')
        return user_name_tag[0].string.strip() if user_name_tag else ''
