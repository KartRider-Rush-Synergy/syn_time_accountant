import cv2
from PIL import Image
from IPython.display import display


def showimg(img):
    scr = Image.fromarray(img)
    display(scr)

def screenshot(d, show=False, target='gray'):
    img = d.screenshot(format='opencv')
    if target == 'gray':
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if target == 'rgb':
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    if show:
        showimg(img)
    return img