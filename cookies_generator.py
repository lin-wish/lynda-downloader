import requests
import sys
from requests.exceptions import ConnectionError as conn_error
import re
import json
from http import cookiejar
import datetime
import pathlib
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USERNAME = 'PACREG348104'
PASSWORD = '123456'
ORGNIZATION = 'hcplonline.org'
ORG_LOGIN_URL = "https://www.lynda.com/signin/organization"
AJAX_ORGNIZATION = "https://www.lynda.com/ajax/signin/organization"
HOMEPAGE = "https://www.lynda.com"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1 Safari/605.1.15',
    'X-Requested-With': 'XMLHttpRequest',
    'Host': 'www.lynda.com'
}
COOKIES_HEADERS = """\
# Netscape HTTP Cookie File
# http://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.
"""
COOKIES_FILE_PATH = os.path.join(str(pathlib.Path(
    __file__).resolve().parent), 'cookies.txt')


def org_login_steps(session, fallback_action_url, extra_form_data, extra_headers, referrer_url):

    if fallback_action_url == AJAX_ORGNIZATION:
        HEADERS.update(
            {'-_-': extra_headers.get('-_-'), 'Referer': referrer_url})
    else:
        HEADERS.update(extra_headers)
        HEADERS.pop('-_-')

    try:
        response = session.post(fallback_action_url,
                                data=extra_form_data, headers=HEADERS)
    except conn_error as e:
        sys.stdout.write(
            "Connection error : {} make sure your internet connection is working.\n".format(e))
        sys.exit(0)
    else:
        if fallback_action_url == AJAX_ORGNIZATION:
            response = response.json()
            _org_url, referrer = response.get('RedirectUrl').replace('http', 'https') if not 'https' in response.get(
                'RedirectUrl') else response.get('RedirectUrl'), response.get('RedirectUrl')
            return _org_url, referrer
        else:
            response = response.text
            logged_in_username = re.search(
                r'data-qa="eyebrow_account_menu">(.*)</span>', response)
            if logged_in_username:
                return logged_in_username.group(1), None
            else:
                return None, None


def get_cookies():
    s = requests.Session()
    try:
        page = s.get(ORG_LOGIN_URL, headers={
                     'User-Agent': HEADERS.get('User-Agent')}).text
    except conn_error as e:
        sys.stdout.write(
            "Connection error : {} make sure your internet connection is working.\n".format(e))
        sys.exit(0)
    else:
        data = re.search(r'var\s+lynda\s+=\s+(?P<data>{.+?});', page)
        if data:
            json_data = json.loads(data.group(1))
            organization_login_url, referrer_url = org_login_steps(
                s, AJAX_ORGNIZATION, {'org': ORGNIZATION}, json_data, ORG_LOGIN_URL)
            try:
                webpage = s.get(referrer_url).text
            except conn_error as e:
                sys.stdout.write(
                    "Connection error : {} make sure your internet connection is working.\n".format(e))
                sys.exit(0)
            else:
                csrftoken = re.search(
                    r'name="seasurf"\s+value="(.*)"', webpage)
                if csrftoken:
                    csrftoken = csrftoken.group(1)
                    login_data = dict(
                        libraryCardNumber=USERNAME,
                        libraryCardPin=PASSWORD,
                        libraryCardPasswordVerify="",
                        org=ORGNIZATION,
                        currentView="login",
                        seasurf=csrftoken
                    )
                    response, _ = org_login_steps(s, organization_login_url, login_data, {
                                                  'Referer': referrer_url}, referrer_url)
                    if response:
                        s.headers.update(
                            {'User-Agent': HEADERS.get('User-Agent')})
                        write_cookies_file(s.cookies)
                        return
                    else:
                        return None
                else:
                    sys.stdout.write("Failed to extract csrftoken.\n")
                    sys.exit(0)
        else:
            sys.stdout.write("Failed to extract login-form..\n")
            sys.exit(0)


def write_cookies_file(cookies):
    expire_date = datetime.datetime.now() + datetime.timedelta(+30)
    expires = str(int(expire_date.timestamp()))
    path = '/'
    secure = 'FALSE'
    domains = cookies.list_domains()
    initial_dot = ''
    cookies_str = ''
    for domain in domains:
        if domain.startswith('.'):
            initial_dot = 'TRUE'
        else:
            initial_dot = 'FALSE'
        cookies_dict = cookies.get_dict(domain=domain)
        for key, value in cookies_dict.items():
            formated_line = "\t".join([domain, initial_dot, path,
                                       secure, expires, key, value]) + "\n"
            cookies_str += formated_line

    with open(COOKIES_FILE_PATH, 'w') as f:
        f.write(COOKIES_HEADERS)
        f.write(cookies_str)
        print('cookies.txt file generated.')


def cookies_init():
    get_cookies()
