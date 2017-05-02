# coding=utf-8
__author__ = 'juraseg'

from lxml import etree
from lxml.html import tostring


def fix_html(html):
    htmlparser = etree.HTMLParser()

    tree = etree.fromstring(html, htmlparser)
    return tostring(tree)