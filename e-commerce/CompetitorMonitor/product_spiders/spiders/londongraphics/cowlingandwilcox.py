# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
import hashlib
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exceptions import DontCloseSpider


class CowlingandwilcoxSpider(BaseSpider):
    name = u'cowlingandwilcox.com'
    allowed_domains = ['www.cowlingandwilcox.com']
    start_urls = ('http://www.cowlingandwilcox.com', )

    def __init__(self, *args, **kwargs):
        super(CowlingandwilcoxSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_all_products, signals.spider_idle)
        self.get_brandless_products = 1

    def process_all_products(self, spider):
        if spider.name == self.name and self.get_brandless_products:
            self.get_brandless_products = 0
            self.log("Spider idle. Processing all products")
            r = Request('http://www.cowlingandwilcox.com/display.aspx?page=all',
                        callback=self.parse_products_list,
                        meta={'category': ''})
            self._crawler.engine.crawl(r, self)
            raise DontCloseSpider

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//a[(@class="region") and (contains(@href, "header"))]/text()').extract()
        urls = hxs.select('//a[(@class="region") and (contains(@href, "header"))]/@href').extract()
        for url, category in zip(urls, categories):
            yield Request(urljoin_rfc(base_url, url + '&page=all'), callback=self.parse_categories, meta={'category': category})

    def parse_categories(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        urls = hxs.select('//*[@id="lblHeader"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list, meta=response.meta)

    def parse_products_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        urls = hxs.select('//a[(@class="region1") and (contains(@href, "detail"))]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        url = urljoin_rfc(base_url, response.url)
        image_url = hxs.select('//*[@id="imgPhototest"]/@src').extract()
        brand = hxs.select('//*[@id="lblSupplier"]/text()').extract()
        brand = brand[0].replace('Manufacturer:', '') if brand else ''
        category = response.meta['category']
        options = hxs.select('//*[@id="dgProducts"]//tr[@style="background-color:Gainsboro;"]')
        ident = response.url.split('productid=')[1]
        for option in options:
            loader = ProductLoader(item=Product(), selector=option)
            name = option.select('./td[1]//span/text()').extract()
            name = ' '.join(x.strip() for x in name).replace("*** Spring Sale ***", '')
            loader.add_value('name', name)
            hash_object = hashlib.md5(name)
            identifier = "{}_{}".format(ident, hash_object.hexdigest())
            loader.add_value('identifier', identifier)
            loader.add_value('url', url)
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = option.select('./td[3]/text()').extract()[0].strip()
            if price == '':
                price = option.select('./td[2]/text()').extract()[0]
            price = extract_price(price.replace(u'\xa3', ''))
            loader.add_value('price', price)
            loader.add_value('brand', brand)
            loader.add_value('category', category)
            in_stock = option.select('./td[1]//b/text()').extract()
            if in_stock:
                if in_stock[0] == 'Out of stock':
                    loader.add_value('stock', 0)
            if price <= 39.99:
                loader.add_value('shipping_cost', 1.95)
            else:
                loader.add_value('shipping_cost', 0)
            yield loader.load_item()
