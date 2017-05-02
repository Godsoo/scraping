# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from decimal import Decimal


class CowlingandwilcoxSpider(BaseSpider):

    name = u'graphicsdirect.co.uk'
    allowed_domains = ['www.graphicsdirect.co.uk']
    start_urls = ('https://www.graphicsdirect.co.uk',)


    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        #categories
        urls = hxs.select('//div[@class="homepage-left"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url))

        #pages
        urls = hxs.select('//a[contains(@class, "i-next")]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url))

        #products
        urls = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        category = hxs.select('//div[contains(@class, "category-title")]/h1/text()').extract()[0].strip() if urls else ''
        for url in urls:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          meta={'category': category})

        #sometimes we may get product page instead of list of products
        if hxs.select('//table[@id="linked-products"]//tr[@class="body"]'):
            category = hxs.select("//div[@class='breadcrumbs']//a")[-1].select("./text()").extract()
            category = category[0].strip() if category else ''
            yield Request(response.url,
                          callback=self.parse_product,
                          meta={'category': category},
                          dont_filter=True)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        options = hxs.select('//table[@id="linked-products"]//tr[@class="body"]')
        image_url = hxs.select('//img[@id="image-main"]/@src').extract()
        image_url = image_url[0] if image_url else ''
        if image_url and 'data:image' in image_url:
            image_url = hxs.select('//img[@id="image-0"]/@data-zoom-image').extract()


        for option in options:

            sku = option.select(".//span[@class='code']/text()").extract()
            name = option.select(".//span[@class='code']/parent::td/text()").extract()
            price = option.select(".//span[@class='price']/text()").extract()
            price = price[0] if price else ''

            if not sku:
                continue
            else:
                sku = sku[0].replace('Code', '').strip()

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', sku)
            loader.add_value('sku', sku)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('url', response.url)
            loader.add_value('category', response.meta.get('category', ''))
            loader.add_value('image_url', image_url)

            if price:
                loader.add_value('stock', 1)
            else:
                loader.add_value('stock', 0)

            price = loader.get_output_value('price')
            if price and price <= 99.99:
                loader.add_value('shipping_cost', 4.99)

            yield loader.load_item()

        if not options:

            sku = hxs.select("//div[@class='product-code']/text()").extract()[0].split(':')[1].strip()
            name = hxs.select("//div[@class='product-name']/h1/text()").extract()[0].strip()
            price = hxs.select("//span[@class='price']/text()").extract()
            price = price[0] if price else ''

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', sku)
            loader.add_value('sku', sku)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('url', response.url)
            loader.add_value('category', response.meta.get('category', ''))
            loader.add_value('image_url', image_url)

            if price:
                loader.add_value('stock', 1)
            else:
                loader.add_value('stock', 0)

            price = loader.get_output_value('price')
            if price and price <= 99.99:
                loader.add_value('shipping_cost', 4.99)

            yield loader.load_item()
