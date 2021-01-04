import requests
from .utils import read_yaml_file, showimg
from pathlib import Path
import base64
from PIL import Image
import numpy as np
import cv2
import logging

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_api_tokens():
    return read_yaml_file(Path(__file__).absolute().parent.parent.joinpath('config/baiduapi.yml'))


def get_access_token():
    url = 'https://aip.baidubce.com/oauth/2.0/token'
    apitoken = get_api_tokens()
    data = {
        'grant_type': 'client_credentials',  # 固定值
    }
    data.update(apitoken)
    res = requests.post(url, data=data)
    res = res.json()
    print(res)
    access_token = res['access_token']
    return access_token


def index_results(res):
    indexed = {}
    for w in res['words_result']:
        if w['words'] not in indexed:
            indexed[w['words']] = [w]
        else:
            indexed[w['words']].append(w)
    return indexed


def get_center(word_res):
    loc = word_res['location']
    y, x, w, h = word_res['location']['top'], word_res['location']['left'], word_res['location']['width'], word_res['location']['height']
    return int(x + w / 2), int(y + h / 2)


def get_middle_point(loc1, loc2, interpolate=0.5):
    alpha = interpolate
    return tuple([int(item) for item in (np.array(loc1) * (1 - alpha) + np.array(loc2) * alpha)])


def get_crossover(loc1, loc2, align='h'):
    if align == 'h':
        return loc2[0], loc1[1]
    if align == 'v':
        return loc1[0], loc2[1]
        

class OCRResult:
    def __init__(self, d, res=None):
        self.res = res if res is not None else None
        self.d = d
       
    def set_res(self, res):
        self.res = res
    
    def word_exists(self, word):
        return word in self.res
    
    def get_center(self, word, occurrence=0):
        return get_center(self.res[word][occurrence])
    
    def click(self, word=None, occurrence=0, loc=None):
        if (word is None) == (loc is None):
            raise ValueError(f"one of (word, loc) must be None")
        if word is not None:
            if not self.word_exists(word):
                raise KeyError(f"Trying to click on {word} which is not on current screen")
            loc = get_center(self.res[word][occurrence])
        self.d.click(*loc)
       
    def drag(self, word1=None, word2=None, occurrence1=0, occurrence2=0, loc1=None, loc2=None, duration=1):
        if ((word1 is None) == (loc1 is None)) or ((word2 is None) == (loc2 is None)):
            raise ValueError(f"one of (word1, loc1) and one of (word2, loc2) must be None")
        if not self.word_exists(word1):
            raise KeyError(f"Word {word1} is not on current screen")
        if not self.word_exists(word2):
            raise KeyError(f"Word {word2} is not on current screen")
            
        if word1 is not None:
            loc1 = get_center(self.res[word1][occurrence1])
        if word2 is not None:
            loc2 = get_center(self.res[word2][occurrence2])
        
        self.d.drag(*loc1, *loc2, duration)
            

def screenshot_ocr(d, engine="webimage_loc", show=False, num_retries=10):
    d.screenshot(Path(__file__).absolute().parent.parent.joinpath('screenshots/current.png'))
    with Path("screenshots/current.png").open('rb') as file:
        img = base64.b64encode(file.read())
    general_word_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/{engine}"
    access_token = get_access_token()
    request_url = general_word_url + "?access_token=" + access_token
    print(request_url)
    params = {"image":img,
              "probability": "true",
             }
    if engine == 'webimage_loc': 
        params["poly_location"] = "true"
    if engine == 'accurate':
        params["vertexes_location"] = "true"
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    got_response = False
    try_num = 0
    while (not got_response) and (try_num < num_retries):
        try_num += 1
        try:
            response = requests.post(request_url, data=params, headers=headers)
        except:
            LOG.info(f"Error getting OCR response, retry #{try_num}")
        else:
            got_response = True
    
    res = response.json()
        
    ss_img = np.array(Image.open('screenshots/current.png'))
    if show:
        for i, word_res in enumerate(res['words_result']):
            prob = word_res['probability']['average']

            text = word_res["words"]
            y, x, w, h = word_res['location']['top'], word_res['location']['left'], word_res['location']['width'], word_res['location']['height']

            # Visualize bbox
            cv2.rectangle(ss_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(ss_img, f"{prob:.2%}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(ss_img, text, (x+100, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        showimg(ss_img)
    return ss_img, OCRResult(d, index_results(res))
