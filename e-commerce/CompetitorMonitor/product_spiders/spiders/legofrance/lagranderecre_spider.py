# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter, url_query_parameter

from product_spiders.utils import extract_price_eu as extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class LaGrandeRecreSpider(BaseSpider):
    name = 'legofrance-lagranderecre.fr'
    allowed_domains = ['lagranderecre.fr']
    start_urls = ('http://www.lagranderecre.fr/lego.html',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="layered-navigation"]//a/@href').extract()
        categories += hxs.select('//div[@class="filter-categories"]//a/@href').extract()
        categories += hxs.select('//div[@class="filter-categories" or @class="filter-cats" or contains(@class, "cat-items")]//a/@href').extract()
        categories += hxs.select('//div[@class="autres_cat"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_urls = hxs.select('//p[contains(@class, "product-name")]//a/@href').extract()
        for url in product_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        if product_urls:
            next_page = str(int(url_query_parameter(response.url, 'p', 0)) + 1)
            next_url = add_or_replace_parameter(response.url, 'p', next_page)
            yield Request(next_url, callback=self.parse_categories)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        l = ProductLoader(item=Product(), response=response)
        identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
        l.add_value('identifier', identifier)
        l.add_xpath('name', '//div[contains(@class, "desc_product")]/h1/text()')
        l.add_value('brand', 'Lego')
        l.add_value('category', 'Lego')
        sku = ''.join(hxs.select('//li[strong[contains(text(), "rence")]]/text()').extract()).strip()
        l.add_value('sku', sku)
        l.add_value('url', response.url)

        price = hxs.select('//form//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//form//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        price = extract_price(price[0]) if price else 0
        l.add_value('price', price)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            l.add_value('image_url', image_url)

        in_stock = hxs.select('//button[@class="button btn-cart"]')
        if not in_stock:
            l.add_value('stock', 0)
        yield l.load_item()
