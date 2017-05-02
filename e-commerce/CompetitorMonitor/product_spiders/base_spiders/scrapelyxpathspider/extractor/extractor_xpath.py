# -*- coding: utf-8 -*-
import requests
from lxml import etree
from lxml.html import make_links_absolute, tostring
from scrapely.htmlpage import dict_to_page

from html_utils import fix_html
from scraper_xpath import ScraperXPath


class ExtractorError(Exception):
    pass


class ExtractorXPath(object):
    def __init__(self, scraper=None):
        if scraper is not None:
            assert isinstance(scraper, ScraperXPath)
        if scraper:
            self.scraper = scraper
        else:
            self.scraper = ScraperXPath()

    @classmethod
    def fromfile(cls, file):
        scraper = ScraperXPath.fromfile(file)
        return cls(scraper)

    def tofile(self, file):
        return self.scraper.tofile(file)

    @staticmethod
    def get_htmlpage(url):
        r = requests.get(url)
        if r.status_code == requests.codes.ok:
            return ExtractorXPath.get_htmlpage_from_text(r.content.decode(r.encoding), url, r)
        else:
            raise ExtractorError("Error %s when loading url '%s'" % (r.status_code, url))

    @staticmethod
    def get_htmlpage_from_text(text, url, r):
        assert isinstance(text, unicode), "unicode expected, got %s" % type(text).__name__
        html = text
        html = fix_html(html)
        html = make_links_absolute(html, base_url=url)
        htmlparser = etree.HTMLParser()
        tree = etree.fromstring(html, htmlparser)
        body = tostring(tree, encoding='unicode')

        headers = dict(r.headers)
        page = dict_to_page({'url': url, 'headers': headers, 'body': body})
        return page

    @staticmethod
    def get_htmlpage_from_text2(text, url, headers):
        assert isinstance(text, unicode), "unicode expected, got %s" % type(text).__name__
        html = text
        html = fix_html(html)
        html = make_links_absolute(html, base_url=url)
        htmlparser = etree.HTMLParser()
        tree = etree.fromstring(html, htmlparser)
        body = tostring(tree, encoding='unicode')

        headers = dict(headers)
        page = dict_to_page({'url': url, 'headers': headers, 'body': body})
        return page

    def train(self, url, data, data_attrs=None):
        r = requests.get(url)
        if r.status_code == requests.codes.ok:
            html = r.content.decode(r.encoding)
            page = self.get_htmlpage_from_text(html, url, r)
            self.scraper.train_from_htmlpage(page, data, data_attrs)
        else:
            raise ExtractorError("Error %s when loading url '%s'" % (r.status_code, url))

    def train_repeated(self, url, data, data_attrs=None):
        r = requests.get(url)
        if r.status_code == requests.codes.ok:
            html = r.content.decode(r.encoding)
            page = self.get_htmlpage_from_text(html, url, r)
            self.scraper.train_from_htmlpage_repeated(page, data, data_attrs)
        else:
            raise ExtractorError("Error %s when loading url '%s'" % (r.status_code, url))

    def scrape_htmlpage(self, page, fields_spec):
        return self.scraper.scrape_page2(page, fields_spec)

    def scrape(self, url, fields_spec):
        page = self.get_htmlpage(url)
        return self.scrape_htmlpage(page, fields_spec)
