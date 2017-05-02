from scrapy.commands import list
from shutil import copyfile

f = list.__file__

copyfile('scrapy_patch/list.py', f.replace('.pyc', '.py'))

