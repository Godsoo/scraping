# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc

from product_spiders.base_spiders.primary_spider import PrimarySpider


class VirginexperiencedaysCoUkSpider(PrimarySpider):
    name = u'virginexperiencedays.co.uk'
    allowed_domains = ['www.virginexperiencedays.co.uk']
    start_urls = [
        'http://www.virginexperiencedays.co.uk/search?pagesize=5000'
    ]

    csv_file = 'virginexperiencedays.co.uk_products.csv'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in response.xpath('//section[@id="results"]//a[contains(@class, "productCard__title")]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = response.xpath('//h1[@class="productHeader__title"]/text()').extract()[0]
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        image_url = response.xpath('//img[contains(@class, "productImages__mainImage")]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        category = response.xpath('//ol[@class="breadcrumbs"]//a/span[text()!="Home"]/text()').extract()[-3:]
        loader.add_value('category', category)
        price = response.xpath('//div[contains(@class, "productMain")]//div[@class="addSection__prices"]/span[@class="currentPrice"]/text()').extract()[0]
        price = extract_price(price)
        loader.add_value('price', price)
        identifier = response.xpath('//input[@id="ProductId"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        sku = response.xpath('//div[contains(@class, "productPage")]/@data-sku').extract()[0]
        loader.add_value('sku', sku)
        yield loader.load_item()
