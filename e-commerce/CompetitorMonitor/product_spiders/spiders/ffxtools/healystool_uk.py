from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

import re
from decimal import Decimal

class HealysToolUK(BaseSpider):
    name = 'healystool.co.uk'
    allow_domains = ['healystool.co.uk']
    start_urls = ['http://www.healystool.co.uk/Delivery---Returns-pg50.aspx']
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        self.shippings = {}
        for tr in hxs.select('//tbody[contains(., "UK Standard")]/tr[position()>3 and position()<9]'):
            weight = tr.select('./td[2]/text()').re('([\d.]+)Kg')
            if not weight:
                break
            weight = Decimal(weight[0])
            if weight not in self.shippings:
                self.shippings[weight] = extract_price(tr.select('./td[3]/text()').extract()[0])
        self.log('Shippings are %s' %self.shippings)
        yield Request('http://www.healystool.co.uk/sitemap.html', callback=self.parse_sitemap)
        
    def parse_sitemap(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@id="content"]/ul/li/ul/li/ul/li/a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_product)
            
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//h2[@class="product-name"]/a/@href').extract():
            yield Request(url, callback=self.parse_product)
        for url in hxs.select('//a[@title="Next"]/@href').extract():
            yield Request(url, callback=self.parse_category)
            
    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_xpath('name', '//div[@class="prodTitle"]/h1/text()')
        loader.add_xpath('price', '//div[@class="pricingSectionIncVat"]/div[@class="ourPriceIncVat"]/text()')
        if not hxs.select('//div[@class="prodFeaturesItem"]/b[text()="Stock:"]/../text()').re('\d+'):
            loader.add_value('stock', 0)
        categories = hxs.select('//div[@id="crumbs"]/a[position()>1]/text()').extract()
        loader.add_value('category', categories[:-1])
        loader.add_xpath('brand', '//div[@class="prodFeaturesItem"]/b[text()="Manufacturer:"]/../text()', re='\S+')
        loader.add_xpath('identifier', '//input[@name="productid"]/@value')
        loader.add_xpath('sku', '//input[@name="productid"]/@value')
        loader.add_value('url', response.url)
        image = hxs.select('//img[@id="bigpic"]/@src').extract()
        if image:
            loader.add_value('image_url', urljoin(base_url, image[0]))
        weight = hxs.select('//div[@class="prodFeaturesItem"]/b[text()="Weight:"]/../text()').re('\S+')
        if loader.get_collected_values('price')[0] > 50*1.2:
            loader.add_value('shipping_cost', 0)
        elif weight:
            weight = extract_price(weight[0])
            weights = sorted(self.shippings)
            for i, w in enumerate(weights):
                if weight < w:
                    continue
                if i + 1 == len(weights) or weight < weights[i+1]:
                    loader.add_value('shipping_cost', self.shippings[w])
                    break
        yield loader.load_item()
