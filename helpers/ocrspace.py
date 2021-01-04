import ocrspace
from pathlib import Path
from PIL import Image
import numpy as np
import cv2
import logging
from .utils import read_yaml_file, showimg
from .ocrprocessing import OCRResult, Word

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def get_api_endpoint(OCREngine=1, isOverlayRequired=True, isTable='true', **kwargs):
    api = ocrspace.API(
        read_yaml_file('config/ocrspaceapi.yml')['key'], 
        OCREngine=OCREngine, 
        isOverlayRequired=isOverlayRequired, 
        isTable=isTable,
        **kwargs
    )
    return api

    
def screenshot_ocr(d, api, show=False):
    d.screenshot(Path(__file__).absolute().parent.parent.joinpath('screenshots/current.png'))
    res = api.ocr_file('screenshots/current.png')
    ss_img = np.array(Image.open('screenshots/current.png'))
    if show:
        for i, line in enumerate(res['TextOverlay']['Lines']):
            for word_res in line['Words']:
                word = Word().parse_ocrspace(word_res)

                # Visualize bbox
                cv2.rectangle(ss_img, (word.left, word.top), (word.right, word.bottom), (0, 255, 0), 2)
                cv2.putText(ss_img, word.text, (word.center), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        showimg(ss_img)
    return ss_img, OCRResult(d, raw=res).parse_raw_ocrspace()
