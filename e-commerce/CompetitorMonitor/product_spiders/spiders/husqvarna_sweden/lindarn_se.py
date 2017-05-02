# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.exceptions import DontCloseSpider
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.utils.url import url_query_parameter


class LindarnSeSpider(BaseSpider):
    name = u'husqvarna_sweden-lindarn.se'
    allowed_domains = ['lindarn.se']
    start_urls = [
        'http://www.lindarn.se'
    ]
    category_urls = []

    def __init__(self, *args, **kwargs):
        super(LindarnSeSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_subcategories, signals.spider_idle)

    def process_subcategories(self, spider):
        if spider.name == self.name:
            self.log("Spider idle. Processing subcategories")
            item = None
            if self.category_urls:
                item = self.category_urls.pop()
            if item:
                r = Request(item['url'], meta={'category': item['category']}, callback=self.parse_products_list)
                self._crawler.engine.crawl(r, self)
                raise DontCloseSpider

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = response.css('.leftside-3').xpath('.//a/text()').extract()
        urls = response.css('.leftside-3').xpath('.//a/@href').extract()
        for category, url in zip(categories, urls):
            self.category_urls.append({'url': urljoin_rfc(base_url, url), 'category': [category.strip(), ]})


    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        for url in response.css('.product-item').xpath('.//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url),
                          meta={'category': response.meta['category']},
                          callback=self.parse_product)
        # subcategories
        categories = response.css('.sub-category-item').xpath('h2/a/text()').extract()
        urls = response.css('.sub-category-item').xpath('h2/a/@href').extract()
        cats = response.meta['category']
        for category, url in zip(categories, urls):
            new_cat = cats[:]
            new_cat.append(category.strip())
            yield Request(urljoin_rfc(base_url, url),
                              meta={'category': new_cat},
                              callback=self.parse_products_list)
        # pages
        for url in response.css('.pager').xpath('.//a/@href').extract():
            yield Request(response.urljoin(url),
                          meta=response.meta,
                          callback=self.parse_products_list)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        image_url = response.css('.picture').xpath('img/@src').extract_first()
        product_identifier = response.xpath('//@data-productid').extract_first()
        product_name = response.xpath('//h1[@itemprop="name"]/text()').extract_first()
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        price = ''.join(response.xpath('//span[@itemprop="price"]/text()').re('\S+'))
        sku = ''.join(response.xpath('//span[@itemprop="sku"]/text()').re('\w+'))
        product_loader.add_value('sku', sku)
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', response.meta['category'][-3:])
        product = product_loader.load_item()
        yield product
