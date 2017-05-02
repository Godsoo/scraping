import csv
import os
import copy
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product
from bablas_item import ProductLoader


class TheWatchHutSpider(BaseSpider):
    name = 'thewatchhut.co.uk'
    allowed_domains = ['thewatchhut.co.uk']
    start_urls = ()
    sku_exclusions = ['tw821', 'tw844']

    errors = []

    def start_requests(self):
        yield FormRequest('http://www.thewatchhut.co.uk/', formdata={'change-currency': 'GB'})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in response.css('.end-link ::attr(href)').extract():
            yield Request(response.urljoin(url))

        product_urls = response.css('.product ::attr(onclick)').re("href='(.+)'")
        for url in product_urls:
            yield FormRequest(response.urljoin(url), callback=self.parse_product, formdata={'change-currency': 'GB'})

        pages = response.css('.pages ::attr(href)').extract()
        for url in pages:
            yield Request(response.urljoin(url))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        if 'DataSet runtime error' in response.body:
            yield response.request.replace(dont_filter=True)
            return

        # Discontinued flag visible
        discontinued = hxs.select('//div[@id="out-stock-form" and contains(@class, "discontinued")]')
        if discontinued:
            return

        # Stock status
        out_stock = response.css('.out-stock')

        category = response.xpath(u'//div[@id="breadcrumb"]/a/text()').extract()
        category = category[-2].strip() if category else ''

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('identifier', '//input[@name="prodId"]/@value')
        loader.add_xpath('identifier', '//script/text()', re='"id":(.+?),')
        loader.add_xpath('name', u'//*[@itemprop="name"]/text()')
        brand = hxs.select('//div[text()="Brand"]/span/text()').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('category', category)

        sku = response.xpath('//div[text()="MPN"]/span/text()').extract()
        if not sku:
            sku = hxs.select('//script/text()').re("'sku'.+'(.+)'")
        sku = sku[0].strip().lower() if sku else ''

        if sku not in self.sku_exclusions:
            sku = re.sub('^(tw)(.*)', '\g<1>0\g<2>', sku)

        if 'police' in loader.get_output_value('name').lower() or 'timberland' in loader.get_output_value('name').lower():
            sku = sku.replace('-', '/')
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        price = response.xpath(u'//*[@itemprop="price"]//text()').extract()
        price = ''.join(price)
        loader.add_value('price', price)
        image = hxs.select(u'//*[@itemprop="image"]//@src').extract()
        image = image[0] if image else ''
        if image:
            image = urljoin_rfc(base_url, image)
            loader.add_value('image_url', image)
        if out_stock:
            loader.add_value('stock', 0)
        yield loader.load_item()
