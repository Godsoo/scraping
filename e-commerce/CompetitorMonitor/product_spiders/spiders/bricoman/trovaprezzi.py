import csv
import os
import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy.utils.response import open_in_browser

HERE = os.path.abspath(os.path.dirname(__file__))

class TrovaprezziSpider(BaseSpider):
    name = 'bricoman-trovaprezzi.it'
    allowed_domains = ['trovaprezzi.it']

    max_retry_count = 5

    errors = []

    def start_requests(self):
        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['bricoman_code']
                yield FormRequest('http://www.trovaprezzi.it/categoria.aspx',
                                  formdata={'libera': row['model'].replace(' ', '+')},
                                  meta={'sku': sku, 'formdata': {'libera': row['model'].replace(' ', '+')}},
                                  callback=self.parse_product)

    def parse(self, response):
        pass

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product = hxs.select('//tr[@class="prodListItem"]')[0]

        if not product.select(u'.//td[@align="right" and @class="prodListPrezzo"]/text()'):
            try_no = response.meta.get('try', 1)
            if try_no < self.max_retry_count:
                meta = {
                    'sku': response.meta['sku'],
                    'try': try_no + 1
                }
                self.log("[WARNING] Retrying. Failed to scrape product price for sku %s from page: %s" %
                         (response.meta['sku'], response.url))
                yield Request(response.url,
                              meta=meta,
                              callback=self.parse_product,
                              dont_filter=True)
            else:
                self.log("[WARNING] Gave up. Failed to scrape product price for sku %s from page: %s" %
                         (response.meta['sku'], response.url))
                self.errors.append("Failed to scrape product price for sku %s from page: %s" %
                                   (response.meta['sku'], response.url))
            return

        loader = ProductLoader(item=Product(), selector=product)
        url = product.select(u'./td/a[b]/@href')[0].extract()
        url = urljoin_rfc(get_base_url(response), url)
        loader.add_value('url', url)
        name = product.select(u'./td/a/b/text()')[0].extract().strip()
        loader.add_value('name', name)
        loader.add_value('sku', response.meta['sku'])
        loader.add_value('identifier', response.meta['sku'])
        price = product.select(u'.//td[@align="right" and @class="prodListPrezzo"]/text()')[0].extract().replace(',', '.')
        loader.add_value('price', price)
        yield loader.load_item()
