import os
import sys
import random
from urllib import urlretrieve
from subprocess import call
from PIL import Image
import numpy as np


def _cut_letters(path, folder, prefix):
    im = Image.open(path)
    col, row =  im.size
    data = np.zeros((row*col, 5))
    pixels = im.load()
    white_count = [0] * col
    for c in range(col):
        white_lines = 0
        for r in range(row):
            if pixels[c, r] > 2:
                white_lines += 1
        white_count[c] = white_lines

    def is_border(c):
        if c < 40:
            return False
        if white_count[c] < 70:
            return False        
        context = [white_count[x] for x in range(c - 5, min(col, c + 5))]
        if max(context) == white_count[c]:
            return True
        return False

    borders = []
    limits = []
    for c in range(col):
        if is_border(c) and (not borders or c-18 > borders[-1]):
            borders.append(c)

    limits.append([0, borders[0]])
    for b in borders[1:]:
        limits.append([limits[-1][1], b])

    top = 0
    bottom = 70

    i = 0
    for left, right in limits:
        cropped = im.crop((left, top, right, bottom))
        cropped.save(os.path.join(folder, '{}_{}.jpg'.format(prefix, i)))
        i += 1
    return i

def _rotate_letters(folder, prefix):
    angles = ['-10', '20', '-30', '20', '-10', '10']
    for i, a in enumerate(angles):
        in_ = os.path.join(folder, prefix + '_{}.jpg'.format(i))
        out_ = os.path.join(folder, prefix + '_{}_rotated.jpg'.format(i))
        call(['convert', in_, '-rotate', a, out_])

def _ocr(folder, prefix):
    captcha = ''
    for x in range(6):
        in_ = os.path.join(folder, prefix + '_{}_rotated.jpg'.format(x))
        out_ = in_.replace('_rotated.jpg', '')
        call(['tesseract', '-psm', '10', in_, out_, 'nobatch', 'letters'])
        captcha += open(out_ + '.txt').read().strip()
    return captcha

def get_captcha(path):
    prefix = path.split('.jpg')[0].split('/')[-1]
    _cut_letters(path, '/tmp', prefix)
    _rotate_letters('/tmp', prefix)
    result = _ocr('/tmp', prefix)
    return result

def get_captcha_from_url(url):
    f = str(random.randint(1, 10000))
    urlretrieve(url, '/tmp/' + f + '.jpg')
    return get_captcha('/tmp/' + f + '.jpg')
    
if __name__ == '__main__':
    image = sys.argv[1]
    print get_captcha(image)
