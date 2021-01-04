import logging
import numpy as np
import time

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_center(word_res):
    y, x, w, h = word_res['Top'], word_res['Left'], word_res['Width'], word_res['Height']
    return int(x + w / 2), int(y + h / 2)


def get_middle_point(loc1, loc2, interpolate=0.5):
    alpha = interpolate
    return tuple([int(item) for item in (np.array(loc1) * (1 - alpha) + np.array(loc2) * alpha)])


def get_crossover(loc1, loc2, align='h'):
    if align == 'h':
        return loc2[0], loc1[1]
    if align == 'v':
        return loc1[0], loc2[1]


def point_in_box(pt, box):
    left, top, right, bottom = box
    return (left <= pt[0] <= right) and (top <= pt[1] <= bottom)

    
class Word:
    def __init__(self):
        self.text = None
        self.line = None
        self.x = None
        self.y = None
        self.w = None
        self.h = None
    
    def __repr__(self):
        return f"Word('{self.text}', ({self.x}, {self.y}, {self.w}, {self.h}))"
    
    def __str__(self):
        return f"Word [{self.text}] in line [{self.line}] at location ({self.x}, {self.y}) with width {self.w} and height {self.h}"

    def parse_ocrspace(self, word):
        self.text = word['WordText']
        self.x = int(word['Left'])
        self.y = int(word['Top'])
        self.w = int(word['Width'])
        self.h = int(word['Height'])
        return self

    @property
    def top(self):
        return self.y
    
    @property
    def bottom(self):
        return self.y + self.h
    
    @property
    def left(self):
        return self.x
    
    @property
    def right(self):
        return self.x + self.w
    
    @property
    def center(self):
        return int(self.x + self.w / 2), int(self.y + self.h / 2)
    
    @property
    def topleft(self):
        return self.left, self.top

    @property
    def topright(self):
        return self.right, self.top
    
    @property
    def bottomleft(self):
        return self.left, self.bottom
    
    @property
    def bottomright(self):
        return self.right, self.bottom

    @property
    def box(self):
        return self.left, self.top, self.right, self.bottom
    
    def in_box(self, box):
        left, top, right, bottom = box
        return all([
            self.x >= left,
            self.y >= top,
            self.x + self.w <= right,
            self.y + self.h <= bottom
        ])
    
    def align(self, word, threshold=10, direction='h'):
        if direction == 'h':
            return self.center[0] - threshold <= word.center[0] <= self.center[0] + threshold
        if direction == 'v':
            return self.center[1] - threshold <= word.center[1] <= self.center[1] + threshold
    
    def vertex_in_other(self, other):
        for v in (self.topleft, self.topright, self.bottomleft, self.bottomright):
            if point_in_box(v, other.box):
                return True
        return False
    
    def overlap(self, word):
        return self.vertex_in_other(word) or word.vertex_in_other(self)
    
    def left_of(self, word):
        return self.right <= word.left

    def right_of(self, word):
        return word.left_of(self)
    
    def top_of(self, word):
        return self.bottom <= word.top
    
    def bottom_of(self, word):
        return word.top_of(self)
    
    def merge(self, word):
        if self.overlap(word):
            raise ValueError('Cannot Merge, words overlap')
        if self.right_of(word) or self.bottom_of(word):
            return word.merge(self)
        newword = Word()
        newword.text = " ".join([self.text, word.text])
        if self.left_of(word):
            newword.x = self.x
            newword.y = min(self.top, word.top)
            newword.w = word.right - self.left
            newword.h = max(self.bottom, word.bottom) - newword.y
            return newword
        if self.top_of(word):
            newword.x = min(self.left, word.left)
            newword.y = self.y
            newword.w = max(self.right, word.right) - newword.x
            newword.h = word.bottom - self.y
            return newword


class OCRResult:
    def __init__(self, d, raw=None):
        self.d = d
        self.raw = raw
        self.res = {}
       
    def parse_raw_ocrspace(self):
        indexed = {}
        for line in self.raw['TextOverlay']['Lines']:
            for w in line['Words']:
                word = Word().parse_ocrspace(w)
                key = word.text.lower()
                if key not in indexed:
                    indexed[key] = [word]
                else:
                    indexed[key].append(word)
        self.res = indexed
        return self
    
    def word_exists(self, word):
        word = word.lower()
        return word in self.res
    
    @property
    def keys(self):
        return list(self.res.keys())
    
    @property
    def words(self):
        words = []
        for word_list in self.res.values():
            words.extend(word_list)
        return words
    
    def get_word(self, word):
        word = word.lower()
        if self.word_exists(word):
            return self.res[word]
        else:
            return []
    
    def get_words_in_box(self, box):
        res_list = []
        for word in self.words:
            if word.in_box(box):
                res_list.append(word)
        return res_list
        
    def num_occurrences(self, word):
        word = word.lower()
        if self.word_exists(word):
            return len(self.res[word])
        else:
            return 0
        
    def handle_location(self, loc):
        new_loc = [int(i) for i in loc]
        if min(new_loc) < 0:
            w, h = self.d.window_size()
            if new_loc[0] < 0:
                new_loc[0] += w
            if new_loc[1] < 0:
                new_loc[1] += h
            
        return new_loc
    
    def get_center(self, word, occurrence=0):
        word = word.lower()
        return self.res[word][occurrence].center
    
    def click(self, word=None, occurrence=0, loc=None):
        if (word is None) == (loc is None):
            raise ValueError(f"one of (word, loc) must be None")
        if word is not None:
            if isinstance(word, str):
                word = word.lower()
                if not self.word_exists(word):
                    raise KeyError(f"Trying to click on {word} which is not on current screen")
                loc = self.res[word][occurrence].center
            else:
                loc = word.center
        loc = self.handle_location(loc)
        LOG.info(f'Clicking {loc}')
        self.d.click(*loc)
       
    def repeat_click(self, word=None, occurrence=0, loc=None, num_clicks=1, delay=3):
        for i in range(num_clicks):
            self.click(word=word, occurrence=occurrence, loc=loc)
            time.sleep(delay)
    
    def drag(self, word1=None, word2=None, occurrence1=0, occurrence2=0, loc1=None, loc2=None, duration=1):
        if ((word1 is None) == (loc1 is None)) or ((word2 is None) == (loc2 is None)):
            raise ValueError(f"one of (word1, loc1) and one of (word2, loc2) must be None")
        if isinstance(word1, str) and (not self.word_exists(word1)):
            raise KeyError(f"Word {word1} is not on current screen")
        if isinstance(word2, str) and (not self.word_exists(word2)):
            raise KeyError(f"Word {word2} is not on current screen")
            
        if word1 is not None:
            if isinstance(word1, str):
                word1 = word1.lower()
                loc1 = self.res[word1][occurrence1].center
            else:
                loc1 = word1.center
        if word2 is not None:
            if isinstance(word2, str):
                word2 = word2.lower()
                loc2 = self.res[word2][occurrence2].center
            else:
                loc2 = word2.center
        
        loc1 = self.handle_location(loc1)
        loc2 = self.handle_location(loc2)
        
        LOG.info(f'Dragging from {loc1} to {loc2}')
        self.d.drag(*loc1, *loc2, duration)