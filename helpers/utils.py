import cv2
from PIL import Image
import yaml
from pathlib import Path
import re
from matplotlib import pylab as plt


def showimg(img):
    scr = Image.fromarray(img)
    fig, ax = plt.subplots(figsize=(15, 15))
    ax.imshow(scr)
    plt.show()

    
def screenshot(d, show=False, target='gray'):
    img = d.screenshot(format='opencv')
    if target == 'gray':
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if target == 'rgb':
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    if show:
        showimg(img)
    return img


def read_yaml_file(file):
    with Path(file).open('r') as file:
        return yaml.load(file, Loader=yaml.FullLoader)
    

def write_yaml_file(obj, file):
    with Path(file).open('w') as file:
        return yaml.dump(obj, file)


def istime(text):
    return re.match("^([0-9]{2}):([0-9]{2}):([0-9]{2})$", text)