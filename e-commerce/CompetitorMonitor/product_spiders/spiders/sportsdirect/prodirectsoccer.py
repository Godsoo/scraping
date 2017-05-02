# -*- coding: utf-8 -*-

from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc

from sportsdirectitems import SportsDirectMeta


class ProDirectSoccerSpider(BaseSpider):
    name = u'sportsdirect-prodirectsoccer.com'
    allowed_domains = ['prodirectsoccer.com']
    start_urls = [
        'http://www.prodirectsoccer.com'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//li[a/text()="Boots"]//div[@class="block first"]/ul[@class="sub-menu"]/li/a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        products = hxs.select('//div[@class="item"]')
        for product in products:
            url = product.select('a/@href').extract()[0]
            brand = product.select('span[contains(@class, "brand")]/text()').extract()
            brand = brand[0] if brand else ''
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'brand':brand})

        nextp = hxs.select('//li[@class="next-page"]/a/@href').extract()
        if nextp:
            yield Request(urljoin_rfc(base_url, nextp[0]))
        

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//h1/text()').extract()[0].strip()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        image_url = hxs.select('//img[@class="product"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        price = hxs.select('//p[@class="price"]/text()').extract()
        price = extract_price(price[0])
        loader.add_value('price', price)
        identifier = hxs.select('//div/@data-quickref').extract()[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('category', response.meta['brand'])
        loader.add_value('brand', response.meta['brand'])

        item = loader.load_item()

        old_price = response.xpath('//div[@id="define-profile"]/p[@class="old-price"]/text()').extract()
        old_price = old_price[0] if old_price else ''
        product_code = response.xpath('//span[@itemprop="mpn"]/text()').extract_first()
        
        size_options = hxs.select('//select[@id="size"]/option[@value!=""]')
        if size_options:
            for size_option in size_options:
                option = deepcopy(item)
                size = ''.join(size_option.select('@value').extract())
                out_of_stock = size_option.select('@disabled').extract()

                option['identifier'] += '-' + size                
                option['name'] += ' ' + size

                if out_of_stock or not option['price']:
                    option['stock'] = 0

                metadata = SportsDirectMeta()
                metadata['size'] = size
                metadata['rrp'] = old_price
                metadata['product_code'] = product_code
                option['metadata'] = metadata
                yield option
        else:
            if not item['price']:
                item['stock'] = 0

            metadata = SportsDirectMeta()
            #metadata['size'] = size
            metadata['rrp'] = old_price
            metadata['product_code'] = product_code
            item['metadata'] = metadata
            yield item
