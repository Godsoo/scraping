# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc

from product_spiders.base_spiders.primary_spider import PrimarySpider
import json

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

class IntoTheBlueSpider(PrimarySpider):
    name = u'buyagift-intotheblue.co.uk'
    allowed_domains = ['intotheblue.co.uk']
    start_urls = ['http://www.intotheblue.co.uk']
    error_urls = []
    csv_file = 'intotheblue.co.uk_products.csv'

    def __init__(self, *args, **kwargs):
        super(IntoTheBlueSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if spider.name == self.name:
            self.log('Spider idle. %d urls to retry' %len(self.error_urls))
            for i, url in enumerate(self.error_urls):
                request = Request(url, dont_filter=True, callback=self.parse_product, meta={'cookiejar':10000+i})
                self._crawler.engine.crawl(request, self)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for i, url in enumerate(hxs.select('//div[@id="navbar"]//li/a/@href').extract()):
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products, meta={'cookiejar':i})

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sub_cats = hxs.select('//div[@class="result"]/div/a/@href').extract()
        for sub_cat in sub_cats:
            yield Request(urljoin_rfc(base_url, sub_cat), callback=self.parse_products, meta=response.meta)

        products = hxs.select('//div[@id="divItemList"]//a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select('//h1/span[@itemprop="name"]/text()').extract()
        if not name:
            yield Request(response.url, dont_filter=True, meta=response.meta, callback=self.parse_products)
        url = response.url
        loader.add_value('url', urljoin_rfc(base_url, url))
        loader.add_value('name', name)
        image_url = hxs.select('//div[@id="carousel-example-generic"]/div/div[1]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        category = hxs.select('//ol[@id="Ol1"]/li/a//text()').extract()
        if category:
            loader.add_value('category', category[-1])

        options = hxs.select('//select[@id="VoucherOption"]/option')

        for option in options:
            value = option.select('@value').extract()[0]
            tries = response.meta.get('try', 0)
            yield FormRequest('https://www.intotheblue.co.uk/Product/PriceandRef', formdata={'SelectedValue':value},
                              dont_filter=True, meta={'loader': loader, 'cookiejar': response.meta['cookiejar'], 'try':tries+1}, 
                              headers={'Referer':response.url}, callback=self.parse_options)
        
        if not options and name:
            loader.add_xpath('identifier', '//label[@id="lblRef"]/text()')
            loader.add_xpath('sku', '//label[@id="lblRef"]/text()')
            loader.add_xpath('price', '//label[@id="lblProductPrice"]//text()')
            yield loader.load_item()

    def parse_options(self, response):
        data = json.loads(response.body)
        loader = response.meta['loader']
        url = response.request.headers['Referer']
        if not data['ProdRef']:
            self.log('%s added to errors' %url)
            self.error_urls.append(url)
            return
        if url in self.error_urls:
            self.error_urls.remove(url)
        loader.replace_value('identifier', data['ProdRef'])
        loader.replace_value('sku', data['ProdRef'])
        loader.replace_value('price', data['ProductPrice'])
        yield loader.load_item()

