# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4579
"""
import re
import json
from urlparse import urljoin

from scrapy import Spider, Request, signals, FormRequest
from scrapy.spiders import CrawlSpider, Rule
from scrapy.utils.response import get_base_url
from scrapy.utils.url import url_query_parameter
from scrapy.linkextractors import LinkExtractor
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import ProductLoaderWithNameStrip as ProductLoader, Product

from specsaversitems import SpecSaversMeta


class EzyVisionSpider(Spider):
    name = 'specsavers_nz-ezyvision.co.nz'
    allowed_domains = ('ezyvision.co.nz', )
    start_urls = ['http://www.ezyvision.co.nz/']
    rules = (Rule(LinkExtractor(allow=('Brand', ))),)

    def __init__(self, *args, **kwargs):
        super(EzyVisionSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        self.log('spider idle called')
        if spider.name == self.name:
            req = Request('http://www.ezyvision.co.nz/search', callback=self.parse_search)
            self.crawler.engine.crawl(req, self)

    def parse(self, response):
        urls = response.xpath('//a/@href').extract()
        urls = [url for url in urls if 'Brand=' in url]
        for url in urls:
            yield Request(urljoin(get_base_url(response), url), callback=self.parse_brand)

    def parse_brand(self, response):
        brand = url_query_parameter(response.url, 'Brand', '')
        urls = response.xpath('//section[@id="productList"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin(get_base_url(response), url), meta={'brand': brand},
                          callback=self.parse_product)

    def parse_search(self, response):

        brand = url_query_parameter(response.url, 'Brand', '')
        urls = response.xpath('//section[@id="productList"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin(get_base_url(response), url), meta={'brand': brand},
                          callback=self.parse_product)

        yield Request('http://www.ezyvision.co.nz/ajax/search', callback=self.parse_ajax_search)

    def parse_ajax_search(self, response):
        base_url = 'http://www.ezyvision.co.nz/product/'
        data = json.loads(response.body)

        if data.get('products', None):
            for product in data['products']:
                yield Request(urljoin(base_url, product['url']), meta={'brand': ''},
                              callback=self.parse_product)

            products_loaded = int(response.meta.get('products_loaded', 6)) + 6
            formdata = {'action': 'load products',
                        'productsLoaded': str(products_loaded)}
            yield FormRequest('http://www.ezyvision.co.nz/ajax/search', dont_filter=True, formdata=formdata,
                              callback=self.parse_ajax_search, meta={'products_loaded': products_loaded})

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//section[@class="product"]//h1/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta.get('brand', ''))
        price = ''.join(response.xpath('//h2[@id="tprices"]/text()').extract())
        loader.add_value('price', price)
        image_url = response.xpath('//figure[@class="main"]//img/@src').extract()[0]
        if image_url.endswith('.jpg'):
            loader.add_value('image_url', urljoin(get_base_url(response), image_url))
        cat = response.xpath('//article[@class="breadcrumbs"]//text()').extract()
        cat = [r for r in cat if r.strip().replace(u'\u203a', '')]
        cat = cat[2:-1]
        for c in cat:
            loader.add_value('category', c)
        loader.add_xpath('identifier', '//input[@name="product_id"]/@value')
        loader.add_xpath('sku', '//input[@name="product_id"]/@value')
        loader.add_value('shipping_cost', '0')
        item = loader.load_item()

        metadata = SpecSaversMeta()
        promotional_data = response.xpath('//font[@color="red" and contains(text(), "use this code")]//text()').extract()
        metadata['promotion'] = ' '.join(promotional_data).strip() if promotional_data else ''
        item['metadata'] = metadata
        yield item
