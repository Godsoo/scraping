# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from utils import extract_price


class FirstincoffeeComSpider(BaseSpider):
    name = '1stincoffee.com'
    allowed_domains = ['1stincoffee.com']
    start_urls = ('http://www.1stincoffee.com/catalog/seo_sitemap/product/',)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//ul[@class="sitemap"]/li/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product)

        pages = set(hxs.select('//div[@class="pages"]//a/@href').extract())
        for url in pages:
            yield Request(urljoin_rfc(base_url, url))


    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//div[@class="product-name"]/h1/text()')[0].extract()

        price = hxs.select('//div[@class="product-main-info"]//div[@class="price-box"]/'
                           'span[contains(@id, "product-price")]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="product-main-info"]//div[@class="price-box"]/'
                               'p[@class="special-price"]/span[@class="price"]/text()').extract()
        price = extract_price(price[0].strip())

        identifier = hxs.select('//p[@class="product-ids"]/text()').re('Product ID: (.*)')[0]
        image_url = hxs.select('//a[@id="main-image"]/@href').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
        category = hxs.select('//div[@class="breadcrumbs"]//a/text()').extract()

        options = hxs.select('//ul[contains(@class, "options-list")]/li')
        if options:
            i = 0
            for opt in options:
                opt_name = opt.select('./span[@class="label"]/label/text()').extract()
                if not opt_name:
                    continue
                opt_name = name + ' ' + opt_name[0].strip()

                opt_price = opt.select('./input/@price').extract()
                if not opt_price:
                    continue
                opt_price = price + extract_price(opt_price[0])

                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('url', response.url)
                loader.add_value('name', opt_name)
                loader.add_value('price', opt_price)
                loader.add_value('sku', identifier)
                loader.add_value('identifier', '%s.%s' % (identifier, i))
                if image_url:
                    loader.add_value('image_url', image_url)
                if category:
                    loader.add_value('category', category[-1])
                if not loader.get_output_value('price'):
                    loader.add_value('stock', 0)

                yield loader.load_item()
                i += 1
        else:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('sku', identifier)
            loader.add_value('identifier', identifier)
            if image_url:
                loader.add_value('image_url', image_url)
            if category:
                loader.add_value('category', category[-1])
            if not loader.get_output_value('price'):
                loader.add_value('stock', 0)

            yield loader.load_item()
