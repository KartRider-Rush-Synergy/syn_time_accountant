from .import utils
from . import ocrspace
from . import navi
import uiautomator2 as u2
import time

import logging
LOG = logging.getLogger(__name__)
logging.basicConfig()

APPNAME = "com.nexon.kart"
API = ocrspace.get_api_endpoint(OCREngine=2, isOverlayRequired=True, isTable='true')


def notice_handler(cur_page):
    if cur_page.name == 'NoticePage':
        cur_page.exit()
        return True
    return False


def start_game(d, show=False, max_wait=180):
    sess = d.session("com.nexon.kart")
    entered = False
    start = time.time()
    while not entered and time.time() - start <= max_wait:
        time.sleep(5)
        ss_img, ocrr = ocrspace.screenshot_ocr(d, API, show=show,)
        cur_page = navi.get_current_page(ocrr)
        if cur_page is None:
            continue
        if notice_handler(cur_page):
            continue
        if cur_page.name == 'StartPage':
            cur_page.start()
            entered = True
    if not entered:
        LOG.error(f'Game did not enter start page within {max_wait} seconds')
        return False
    
    at_home_page = False
    while not at_home_page and time.time() - start <= max_wait:
        time.sleep(5)
        ss_img, ocrr = ocrspace.screenshot_ocr(d, API, show=show,)
        cur_page = navi.get_current_page(ocrr)
        if cur_page is None:
            continue
        if notice_handler(cur_page):
            continue
        if cur_page.name == 'WelcomePage':
            cur_page.exit()
        if cur_page.name == 'SignInRewardsPage':
            cur_page.exit()
        if cur_page.name == 'EventsPage':
            cur_page.claims()
            cur_page.exit()
        if cur_page.name == 'HomePage':
            at_home_page = True

    return at_home_page


def add_clubmember_as_friends(d, show=False, max_wait=600):
    ss_img, ocrr = ocrspace.screenshot_ocr(d, API, show=show,)
    cur_page = navi.get_current_page(ocrr)
    if not cur_page.name in ('HomePage'):
        raise TypeError('Need to start at home page to run this function')
