import numpy as np
import re
from .utils import istime
import logging

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
            
def verify_page(words, ocrr, nmatch=0): 
        """
        
        Parameters
        ----------
        words: list of str
            words that identifies a page
        ocrr: OCRResults
            output from screenshot_ocr function
        
        Returns
        -------
        bool
        """
        if nmatch <= 0 or nmatch >= len(words):
            return all([ocrr.word_exists(word) for word in words])
        return sum([ocrr.word_exists(word) for word in words]) > nmatch


def parse_member_names(member_name_words):
    member_names_aligned = []
    for word in member_name_words:
        assigned = False
        for existing in member_names_aligned:
            for existing_word in existing:
                if word.align(existing_word, threshold=20, direction='v'):
                    for i, item in enumerate(existing):
                        if word.left_of(item):
                            existing.insert(i, word)
                            assigned = True
                            break
                    if not assigned:
                        existing.append(word)
                        assigned = True
                    break
            if assigned:
                break
        if not assigned:
            member_names_aligned.append([word])

    member_names = []
    for line in member_names_aligned:
        if len(line) > 1:
            # Remove name parts with no more than 2 characters due to special character
            newline = []
            for word in line:
                if len(word.text) > 2:
                    newline.append(word)
        else:
            newline = line
        cur_word = newline[0]
        if len(newline) > 1:
            for name in newline[1:]:
                cur_word = cur_word.merge(name)
        # remove syn tag
        if cur_word.text.endswith('syn'):
            cur_word.text = cur_word.text[:-3]
        if cur_word.text.startswith('9'):
            cur_word.text = cur_word.text[1:]
        member_names.append(cur_word)

    return member_names
    

def sort_words(word_list, direction='h'):
    if direction == 'v':
        gt = 'bottom_of'
    if direction == 'h':
        gt = 'right_of'
    
    newlist = []
    for word in word_list:
        assigned = False
        for i, w in enumerate(newlist):
            if getattr(w, gt)(word):
                newlist.insert(i, word)
                assigned = True
                break
        if not assigned:
            newlist.append(word)
    
    return newlist


class Page:
    def __init__(self, name=None, ocrr=None):
        self.name = name
        self.ocrr = ocrr
        self.links = {}
    
    def __repr__(self):
        return f"Page({self.name})"

    def __str__(self):
        return self.__repr__()

    
class NoticePage(Page):
    def __init__(self, ocrr):
        super().__init__(name='NoticePage', ocrr=ocrr)
    
    def verify(self):
        return verify_page(['Notice', "OK"], self.ocrr)

    def exit(self):
        self.ocrr.click("OK")

    
class StartPage(Page):
    def __init__(self, ocrr):
        super().__init__(name='StartPage', ocrr=ocrr)
    
    def verify(self):
        return verify_page(['Start', "Log", 'Out'], self.ocrr)

    def start(self):
        self.ocrr.click("Start")

    
class TrackSelectionPage(Page):
    def __init__(self, ocrr):
        super().__init__(name="TrackSelectionPage", ocrr=ocrr)
    
    def verify(self):
        return verify_page(['Select', "Track", "All"], self.ocrr)
    
    def scroll(self, direction='down', duration=0.2):
        # take tracke (only ones with brackets)
        track_words = []
        for w, word_list in self.ocrr.res.items():
            if ("(" in w) or (")" in w):
                track_words.extend(word_list)
        top_loc = min([word.top for word in track_words])
        mid_loc = np.mean([min([word.left for word in track_words]), max([word.left for word in track_words])])
        bottom_loc = max([word.top for word in track_words])
        
        if direction == "down":
            self.ocrr.drag(loc1=[mid_loc, bottom_loc], loc2=[mid_loc, top_loc], duration=duration)
        if direction == "up":
            self.ocrr.drag(loc1=[mid_loc, top_loc], loc2=[mid_loc, bottom_loc], duration=duration)
        
    def exit(self):
        self.ocrr.click(loc=[-60, 60])
    
    def select_map(self, map_name):
        # TODO
        # scrolls to search for map
        # builds a database of map locations so in the future don't need to screenshot at every scroll
        pass

        
class TimeTrialHomePage(Page):
    def __init__(self, ocrr):
        super().__init__(name="TimeTrialHomePage", ocrr=ocrr)
    
    def verify(self):
        return verify_page(['Time', 'Trial', 'Start'], self.ocrr)
        
    def get_name_time_pairs(self):
        #TODO
        # returns a list of tuples (name_word, time_word)
        server_words = self.ocrr.get_word('Server')
        largest_left = 0
        for w in server_words:
            if w.left > largest_left:
                right_loc = w.left
                top_loc = w.bottom + 40
                largest_left = w.left
        
        ranking_words = self.ocrr.get_word('Ranking')
        largest_top = 0
        for w in ranking_words:
            if w.top > largest_top:
                left_loc = w.right + 140
                bottom_loc = w.top - 90
                largest_top = w.top
        
        name_time_words = self.ocrr.get_words_in_box(box=(left_loc, top_loc, right_loc, bottom_loc))
        members = []
        times = []
        for word in name_time_words:
            if istime(word.text):
                times.append(word)
            else:
                members.append(word)
        
        members_clean = parse_member_names(members)
        
        sorted_all = sort_words(members_clean + times, direction='v')
        
        N = len(sorted_all)
        pairs = []
        for i, word in enumerate(sorted_all):
            if not istime(word.text):
                if i < N-1:
                    nxt = sorted_all[i + 1]
                    if istime(nxt.text):
                        pairs.append((word, nxt))
        
        return pairs
    
    def scroll(self, direction='down', duration=0.2):
        name_time_pairs = self.get_name_time_pairs()
        #TODO
    
    def exit(self):
        self.ocrr.click(loc=[50, 20])
    
    def change_map(self):
        self.ocrr.click("Edit")
        

class StartGameHomePage(Page):
    def __init__(self, ocrr):
        super().__init__(name="StartGameHomePage", ocrr=ocrr)
    
    def verify(self):
        return verify_page(['Select', 'Mode', 'Training'], self.ocrr)
    
    def timetrial(self):
        self.ocrr.click("Trial")
        
    def exit(self):
        self.ocrr.click(loc=[50, 20])
        

class SignInRewardsPage(Page):
    def __init__(self, ocrr):
        super().__init__(name="SignInRewardsPage", ocrr=ocrr)
    
    def verify(self):
        return (
            verify_page(['Sign', 'Great', 'Gifts', 'AllWeek', 'Week'], self.ocrr, nmatch=3)
        )
    
    def exit(self):
        if self.ocrr.word_exists("X"):
            self.ocrr.click("X")
        else:
            self.ocrr.click(loc=[-170, 100])
        

class WelcomePage(Page):
    def __init__(self, ocrr):
        super().__init__(name="WelcomePage", ocrr=ocrr)
    
    def verify(self):
        return (
            verify_page(['CODEX'], self.ocrr)
        )
    
    def exit(self):
        if self.ocrr.word_exists("X"):
            self.ocrr.click("X")
        else:
            self.ocrr.click(loc=[-140, 170])



class EventsPage(Page):
    def __init__(self, ocrr):
        super().__init__(name="EventsPage", ocrr=ocrr)
    
    def verify(self):
        return (
            verify_page(['Daily', 'Events'], self.ocrr) or
            verify_page(['Event', 'Center'], self.ocrr)
        )
    
    def claims(self):
        LOG.info('Claiming rewards...')
        for i in range(self.ocrr.num_occurrences("Claim"))[::-1]:
            self.ocrr.repeat_click(word='Claim', occurrence=i, num_clicks=5, delay=1)
    
    def exit(self):
        if self.ocrr.word_exists("X"):
            self.ocrr.click("X")
        else:
            self.ocrr.click(loc=[-140, 170])

        
class HomePage(Page):
    def __init__(self, ocrr):
        super().__init__(name="HomePage", ocrr=ocrr)
    
    def verify(self):
        return (
            verify_page(['Potential', 'Practice', 'StorageStart', 'Game'], self.ocrr, nmatch=2) or
            verify_page(['Start', 'Game'], self.ocrr)
        )
    
    def club_page(self):
        self.ocrr.click('Club')
    
    def start_game(self):
        self.ocrr.click('Game')
        

class ClubHomePage(Page):
    def __init__(self, ocrr):
        super().__init__(name="ClubHomePage", ocrr=ocrr)
    
    def verify(self):
        return (
            verify_page(['Club', 'CP', 'League', 'Special', 'Drill'], self.ocrr, nmatch=3)
        )
    
    def members(self):
        self.ocrr.click("Members")
    
    def exit(self):
        self.ocrr.click(loc=[50, 10])
        

class ClubMembersPage(Page):
    def __init__(self, ocrr):
        super().__init__(name="ClubMembersPage", ocrr=ocrr)
        self.members = None
    
    def verify(self):
        return (
            verify_page(['Club', 'Name', 'Position', 'Tier', 'Status', 'Activity'], self.ocrr, nmatch=4)
        )
    
    def get_members(self):
        # Get all the names underneath "Name" column
        # left bounded by right of "Club" from "Leave Club"
        # right bounded by left of "Position"
        leave_words = self.ocrr.get_word('Club')
        largest_top = 0
        for w in leave_words:
            if w.top > largest_top:
                left_loc = w.left + 5
                largest_top = w.top
                bottom_loc = largest_top - 100
        
        position_words = self.ocrr.get_word('Position')
        smallest_top = float('inf')
        for w in position_words:
            if w.top < smallest_top:
                right_loc = w.left - 5
                smallest_top = w.top
                top_loc = w.bottom + 50
        
        # get words between these locs
        member_name_words = self.ocrr.get_words_in_box(box=(left_loc, top_loc, right_loc, bottom_loc))
        self.members = parse_member_names(member_name_words)
        
    def scroll(self, direction='down', duration=0.2):
        if self.members is None:
            self.get_member_names()
            
        top = None
        bottom = None
        top_loc = float('inf')
        bottom_loc = 0
        for member in self.members:
            if member.top < top_loc:
                upper_loc = member.center
                top_loc = member.top
            if member.bottom > bottom_loc:
                lower_loc = member.center
                bottom_loc = member.bottom
        
        if direction == "down":
            self.ocrr.drag(loc1=lower_loc, loc2=upper_loc, duration=duration)
        if direction == "up":
            self.ocrr.drag(loc1=upper_loc, loc2=lower_loc, duration=duration)
    
    def add_friend(self, member):
        if not self.ocrr.word_exists('Status'):
            raise KeyError('Word "Status" not found')
        if member not in self.members:
            raise KeyError(f'member {member} is not in self.members')
        
        self.ocrr.click(member)
        
        time.sleep(2)
        vertical_align = self.ocrr.get_word("Status")[0].left - 50
        self.ocrr.click(loc=[vertical_align, member.center[1]])
        
    def exit(self):
        self.ocrr.click(loc=[50, 10])


class AddFriendPage(Page):
    def __init__(self, ocrr):
        super().__init__(name='AddFriendPage', ocrr=ocrr)
    
    def verify(self):
        return verify_page(['Add', "as", 'Friend', 'OK'], self.ocrr)
    
    def confirm(self):
        self.ocrr.click('OK')


PAGES = [
    StartPage,
    WelcomePage,
    SignInRewardsPage,
    EventsPage,
    NoticePage, 
    TrackSelectionPage, 
    TimeTrialHomePage, 
    StartGameHomePage, 
    HomePage,
    ClubHomePage,
    ClubMembersPage,
    AddFriendPage,
]


def get_current_page(ocrr):
    for page in PAGES:
        page_item = page(ocrr)
        if page_item.verify():
            return page_item
    return None

