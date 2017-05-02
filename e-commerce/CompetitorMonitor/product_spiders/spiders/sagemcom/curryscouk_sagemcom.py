__author__ = 'juraseg'

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest

from product_spiders.items import Product, ProductLoader

import logging
import re
from utils import get_product_list

class CurrysCoUkSpiderSagemcom(BaseSpider):
    name = 'currys.co.uk_sagemcom'
    allowed_domains = ['currys.co.uk']
    search_url = 'http://www.currys.co.uk/gbuk/s_action/search_keywords/index.html'

    def start_requests(self):
        for row in get_product_list('Currys'):
            if row['url']:
                yield Request(row['url'], callback=self.parse_product, meta=row)
            else:
                data = {
                    'subaction': 'keyword_search',
                    'search-field': row['search'].pop(0)
                }
                url = self.search_url
                yield FormRequest(url, formdata=data, callback=self.parse_search, meta=row)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url

        name = hxs.select("//h1[@class='pageTitle']/span/text()").extract()
        if not name:
            logging.error("ERROR! NO NAME! %s" % url)
            return
        name = " ".join(name)
        name = re.sub("[\s]+", " ", name)

        price = hxs.select("//div[contains(@class, 'productDetail')]//span[contains(@class, 'currentPrice')]/ins/text()").extract()
        if not price:
            logging.error("ERROR! NO PRICE! %s %s" % (url, name))
            return
        price = price[0]


        l = ProductLoader(item=Product(), selector=hxs)
        l.add_value('identifier', name)
        l.add_value('name', name)
        l.add_value('url', url)
        l.add_value('price', price)
        l.add_value('sku', response.meta['sku'])
        l.add_value('brand', response.meta['brand'])
        l.add_value('category', response.meta['category'])
        l.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        if hxs.select('//span[@class="available"]/i[@class="icon-ok"]'):
            l.add_value('stock', '1')
        else:
            l.add_value('stock', '0')
        l.add_value('shipping_cost', '0')
        yield l.load_item()

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        # parse pages
        pages = hxs.select("//ul[@class='pagination']//a/@href").extract()
        for page in pages:
            if page != '#':
                request = Request(page, callback=self.parse_search, meta=response.meta)
                yield request

        found = False
        for url in hxs.select("//div/header[@class='productTitle']/a/@href").extract():
            found = True
            yield Request(url, callback=self.parse_product, meta=response.meta)

        if not found and response.meta['search']:
            data = {
                'subaction': 'keyword_search',
                'search-field': response.meta['search'].pop(0)
            }
            url = self.search_url
            yield FormRequest(url, formdata=data, callback=self.parse_search, meta=response.meta)
