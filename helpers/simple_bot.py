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


def check_at_page(d, target_page_names, retry_wait=2, max_wait=10, show=False):
    at_target = False
    start = time.time()
    while not at_target and time.time() - start <= max_wait:
        time.sleep(retry_wait)
        ss_img, ocrr = ocrspace.screenshot_ocr(d, API, show=show,)
        cur_page = navi.get_current_page(ocrr)
        if cur_page is None:
            continue
        if notice_handler(cur_page):
            continue
        if cur_page.name in target_page_names:
            at_target = True

    return at_target, cur_page


def start_game(d, show=False, max_wait=180):
    sess = d.session("com.nexon.kart")
    entered = False
    start = time.time()
    at_start, cur_page = check_at_page(
        d, 'StartPage', retry_wait=5, max_wait=max_wait, show=show)
    if at_start:
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


def enter_club_members_page(d, show=False):
    ss_img, ocrr = ocrspace.screenshot_ocr(d, API, show=show,)
    cur_page = navi.get_current_page(ocrr)
    if not cur_page.name in ('HomePage'):
        raise RuntimeError('Need to start at home page to run this function')

    cur_page.club_page()
    at_club_page, cur_page = check_at_page(d, ["ClubHomePage"], show=show)
    if not at_club_page:
        raise RuntimeError("Cannot enter club home page")
    cur_page.members()
    at_members_page, cur_page = check_at_page(d, ["ClubMembersPage"], show=show)
    if not at_members_page:
        raise RuntimeError("Cannot enter club members page")

    return at_members_page


def add_friends(d, show=False, max_wait=900):
    ss_img, ocrr = ocrspace.screenshot_ocr(d, API, show=show,)
    cur_page = navi.get_current_page(ocrr)
    if not cur_page.name == "ClubMembersPage":
        raise RuntimeError(
            "Need to start at the club members page to run this function")

    start = time.time()
    added = []
    while start - time.time() <= max_wait:
        # get list
        cur_page.get_members()
        unadded = [m for m in cur_page.members if m.text not in added]
        if len(unadded) == 0:
            return True
        for member in unadded:
            cur_page.click_member(member)
            time.sleep(1)
            page_change = False
            tries = 0
            while not page_change and tries < 5:
                tries += 1
                cur_page.add_friend(member)
                page_change, landing_page = check_at_page(
                    d, ["AddFriendPage", "ChatPage"],
                    retry_wait=1,
                    max_wait=5,
                    show=show
                )
                if landing_page.name == 'AddFriendPage':
                    landing_page.confirm()
                if landing_page.name == 'ChatPage':
                    landing_page.exit()
            time.sleep(2)

        added.extend([m.text for m in cur_page.members])
        cur_page.scroll(direction='down')
        ss_img, ocrr = ocrspace.screenshot_ocr(d, API, show=show,)
        cur_page = navi.get_current_page(ocrr)
        if not cur_page.name == "ClubMembersPage":
            raise RuntimeError("Unexpected exit from club members page")

    return False
