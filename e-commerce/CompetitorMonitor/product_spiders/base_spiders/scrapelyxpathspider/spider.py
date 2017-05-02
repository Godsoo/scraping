# coding=utf-8
__author__ = 'juraseg'

import os.path
import sys
import json
from datetime import datetime
from urlparse import urlparse
from urlparse import urljoin
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from scrapy.spider import BaseSpider
from scrapy.http.request import Request
from scrapy.utils.response import get_base_url
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import CloseSpider

from product_spiders.items import ProductLoaderWithNameStrip as ProductLoader, Product
from product_spiders.utils import check_is_url

from product_spiders.base_spiders.scrapelyxpathspider.extractor.extractor_xpath import ExtractorXPath

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(HERE, '../../../productspidersweb')))

from productspidersweb.models import Spider, ScrapelySpiderData, ScrapelySpiderExtractor
from product_spiders.db import Session


class ScrapelySpider(BaseSpider):
    def __init__(self, name, *args, **kwargs):
        self.name = name
        
        db_session = Session()
        self.db_spider = db_session.query(Spider).filter(Spider.name == self.name).first()
        if not self.db_spider:
            raise CloseSpider("Spider %s not found" % self.name)
        self.db_scrapely_spider = db_session.query(ScrapelySpiderData)\
            .filter(ScrapelySpiderData.spider_id == self.db_spider.id)\
            .first()
        if not self.db_scrapely_spider:
            raise CloseSpider("Scrapely config for spider %s not found" % self.name)
        db_extractors = db_session.query(ScrapelySpiderExtractor)\
            .filter(ScrapelySpiderExtractor.scrapely_spider_data_id == self.db_scrapely_spider.id)
        if not db_extractors.count():
            raise CloseSpider("Scrapely extractors for spider %s not found" % self.name)

        self.allowed_domains = []
        self.start_urls = []

        for url in json.loads(self.db_scrapely_spider.start_urls_json):
            domain, start_url = _parse_start_url(url)
            self.allowed_domains.append(domain)
            self.start_urls.append(start_url)

        domain, start_url = _parse_start_url(self.db_scrapely_spider.start_url)
        self.allowed_domains.append(domain)
        self.start_urls.append(start_url)
        
        super(ScrapelySpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self._spider_idle, signals.spider_idle)
        dispatcher.connect(self._spider_opened, signals.spider_opened)
        dispatcher.connect(self._spider_closed, signals.spider_closed)

        db_session.close()

    def _train_extractors(self):
        xpath_extractors = []
        # train
        self.log("Training templates")
        for ex in self.db_scrapely_spider.extractors:
            xpath_extractor = ExtractorXPath.fromfile(StringIO(ex.templates_json))
            fields_spec = json.loads(ex.fields_spec_json)
            xpath_extractors.append((ex, xpath_extractor, fields_spec))
        self.log("Finished training")
        return xpath_extractors

    def _spider_opened(self, spider):
        if spider.name == self.name:
            self.start_time = datetime.now()

            self.xpath_extractors = self._train_extractors()
            if not self.xpath_extractors:
                msg = "Failed to train crawler for %s" % self.website_db.name
                self.log(msg)
                raise CloseSpider(msg)

    def _spider_closed(self, spider):
        self.end_time = datetime.now()

    def _spider_idle(self, spider):
        pass

    def parse(self, response):
        htmlpage = ExtractorXPath.get_htmlpage_from_text2(response.body_as_unicode(), response.url, response.headers)

        for ex, xpath_extractor, fields_spec in self.xpath_extractors:
            res = xpath_extractor.scrape_htmlpage(htmlpage, fields_spec)
            if ex.type == 'links_list' and res is not None:
                for r in res:
                    # print "Got %d links" % len(r['link'])
                    for new_url in r['link']:
                        if check_is_url(new_url):
                            new_url = urljoin(get_base_url(response), new_url)
                            yield Request(
                                url=new_url,
                                callback=self.parse,
                                errback=self.parse_error,
                            )
            elif ex.type == 'product_details' and res is not None:
                for r in res:
                    for field, value in r.items():
                        while isinstance(value, list):
                            value = value.pop()
                        r[field] = value
                    identifier = r.get('identifier')
                    if not identifier:
                        identifier = r.get('name')
                    if not identifier:
                        self.log("Product with no identifier and name. Skipping...")
                        continue

                    loader = ProductLoader(Product(), response=response)
                    loader.add_value('identifier', identifier)
                    for field, value in r.items():
                        if field == 'image':
                            field = 'image_url'
                        if field == 'stock':
                            if isinstance(value, bool):
                                if value:
                                    value = None
                                else:
                                    value = 0
                            elif isinstance(value, str) or isinstance(value, unicode):
                                if 'in stock' in value.lower():
                                    value = None
                                elif 'out of stock' in value.lower():
                                    value = 0
                                else:
                                    value = None
                        loader.add_value(field, value)
                    loader.add_value('url', response.url)
                    yield loader.load_item()

    def parse_error(self, *args, **kwargs):
        pass

def _parse_start_url(url):
    r = urlparse(url)
    if r.netloc and r.scheme:
        domain = r.netloc
        start_url = url
    else:
        domain = url
        start_url = 'http://' + url
    return domain, start_url
