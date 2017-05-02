# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider


class OncallmedicalsuppliesSpider(BaseSpider):
    name = u'oncallmedicalsupplies.co.uk'
    allowed_domains = ['www.oncallmedicalsupplies.co.uk']
    start_urls = [
        u'http://www.oncallmedicalsupplies.co.uk',
    ]
    #download_delay = 1

    def __init__(self, *args, **kwargs):
        super(OncallmedicalsuppliesSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_subcategories, signals.spider_idle)

        self.subcategories = []

    def process_subcategories(self, spider):
        if spider.name == self.name:
            self.log("Spider idle. Processing subcategories")
            url = None
            if self.subcategories:
                url = self.subcategories.pop(0)
            if url:
                r = Request(url, callback=self.parse_subcategories)
                self._crawler.engine.crawl(r, self)
                raise DontCloseSpider

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # subcategories
        urls = hxs.select('//div[@class="nav-container"]//ul[@class="nav-horizontal"]/li[position() > 1 and position() < 7]//a/@href').extract()
        for url in urls:
            url = urljoin_rfc(base_url, url)
            if url not in self.subcategories:
                self.subcategories.append(url)
            #yield Request(urljoin_rfc(base_url, url), callback=self.parse_subcategories)

        brand_list = "http://www.oncallmedicalsupplies.co.uk/brands/"
        yield Request(brand_list, callback=self.parse_brand_list)

    def parse_brand_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        urls = response.xpath('//ul[@id="manufacturer_list"]//a/@href').extract()
        for url in urls:
            url = urljoin_rfc(base_url, url)
            if url not in self.subcategories:
                self.subcategories.append(url)


    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # subcategories
        urls = hxs.select('//*[@id="narrow-by-list2"]//a/@href').extract()
        for url in urls:
            url = urljoin_rfc(base_url, url)
            if url not in self.subcategories:
                self.subcategories.append(url)
            #yield Request(urljoin_rfc(base_url, url), callback=self.parse_subcategories)
        urls = hxs.select('//div[@class="category-description std"]/table//a/@href').extract()
        for url in urls:
            url = urljoin_rfc(base_url, url)
            if url not in self.subcategories:
                self.subcategories.append(url)
            #yield Request(urljoin_rfc(base_url, url), callback=self.parse_subcategories)
        #pagination
        urls = hxs.select('//div[@class="pages"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_subcategories)
        # products
        urls = hxs.select('//div[@class="category-products"]//h2/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in response.xpath('//div[@class="grouped_mini_name"]/a/@href').extract():
            yield Request(url, callback=self.parse_product)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        image_url = hxs.select('//img[@id="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin(base_url, image_url[0]))
        identifier = response.xpath('//*[@id="product_addtocart_form"]//input[@name="product"]/@value').extract()[0].strip()
        price = 0
        availability = hxs.select('//span[@itemprop="availability"]/@content').extract()
        if availability:
            if availability[0].strip() == 'out_of_stock':
                loader.add_value('stock', 0)
            else:
                price = response.xpath('//span[@id="price-excluding-tax-%s"]//text()' %identifier).extract()
                if price:
                    price = extract_price(price[0])
                else:
                    return
        loader.add_value('price', price)
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li[2]/a/text()').extract()
        if category:
            loader.add_value('category', category[-1])
        sku = hxs.select('//span[@itemprop="identifier"]/text()').extract()[0]
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        brand = hxs.select('//span[@itemprop="brand"]/text()').extract()
        if brand:
            loader.add_value('brand', brand[0])
        yield loader.load_item()
