# -*- coding: utf-8 -*-

import os
import csv
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.config import DATA_DIR
from product_spiders.base_spiders.walmartspider import WalmartSpider


class LegoUSAWalmartSpider(WalmartSpider):
    HERE = os.path.abspath(os.path.dirname(__file__))
    enable_map = True
    name = 'legousa-walmart.com'
    allowed_domains = ['walmart.com', 'walmart.ugc.bazaarvoice.com']
    start_urls = ('http://www.walmart.com/search/search-ng.do?Find=Find&_refineresult=true&ic=16_0&'
                  'search_constraint=0&search_query=LEGO&facet=retailer%3AWalmart.com%7C%7Cbrand%3ALEGO',
                  'http://www.walmart.com/search/search-ng.do?query=LEGO&cat_id=4171&facet=retailer%3AWalmart.com&search_constraint=4171',)

    def __init__(self, *args, **kwargs):
        super(WalmartSpider, self).__init__(*args, **kwargs)

        self.errors = []
        self.map_screenshot_html_files = {}

    def start_requests(self):
        # Parse default items and then start_urls
        yield Request('http://www.walmart.com', self.parse_default)

    def parse_default(self, response):
        if hasattr(self, 'prev_crawl_id') and False: # this is temporarily disabled to extract only the items sold by Walmart directly
            with open(os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield Request(row['url'], callback=self.parse_product)

        # Scrape start urls
        for url in self.start_urls:
            yield Request(url, meta={'real_crawl': True})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        real_crawl = response.meta.get('real_crawl', False)

        items = hxs.select('//div[@id="tile-container"]//a[@class="js-product-title"]/@href').extract()
        for url in items:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        next_pages = hxs.select('//a[contains(@class,"paginator-btn")]/@href').extract()
        if next_pages:
            for next_page in next_pages:
                yield Request(urljoin_rfc(base_url, next_page), meta=response.meta)

        if not items and not next_pages and real_crawl:
            self.errors.append('WARNING: No items => %s' % response.url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        if 'WALMART' not in ''.join(response.xpath('//div[contains(@class, "seller-info")]//span[@class="seller-walmart"]//b/text()').extract()).upper():
            self.log('Not sold by Walmart. Skipping: {}'.format(response.url))
            return
        for elem in super(LegoUSAWalmartSpider, self).parse_product(response):
            yield elem
