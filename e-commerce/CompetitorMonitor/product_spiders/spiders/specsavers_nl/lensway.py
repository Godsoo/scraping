# -*- coding: utf-8 -*-
"""
Customer: Specsavers NL
Website: https://www.lensway.nl
All products Lenzen category

Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5106

"""

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
from urlparse import urljoin

from product_spiders.utils import extract_price_eu as extract_price

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from product_spiders.spiders.specsavers_nz.specsaversitems import SpecSaversMeta


class Lensway(BaseSpider):
    name = "specsavers_nl-lensway.nl"
    allowed_domains = ["lensway.nl"]
    start_urls = ['https://www.lensway.nl/contactlenzen/?sort=name&_page=15']

    def parse(self, response):
        base_url = get_base_url(response)

        for url in response.css('.product-item ::attr(href)').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)

        replacement = response.xpath('//a[@class="replacementUrl" and not(@href="#") and not(@href="")]/@href').extract()
        if replacement:
            yield Request(urljoin(base_url, replacement[0]), callback=self.parse_product)
            return

        name = response.css('.product-info ::text').extract()
        name = ' '.join(name).strip()
        size = response.css('.checked span::text').extract_first()
        if size:
            name += ' ' + size.strip()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name.strip())
        price = response.xpath(".//span[not(@id)][not(@style)][contains(concat(' ',normalize-space(@class),' '),\" inline price bold productInfo-orgPrice product-info-price-current \")]/text()").extract()
        price = extract_price(price[0]) if price else 0
        loader.add_value('price', price)
        image_url = response.xpath('//img[@id="product-image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', 'http:' + image_url[0])
        loader.add_xpath('brand', '//meta[@itemprop="manufacturer"]/@content')
        category = response.css('.breadcrumbs span::text').extract()[1:-1]
        if category:
            loader.add_value('category', category)
        loader.add_value('url', response.url)
        try:
            identifier = response.xpath('//input[@name="prodid"]/@value').extract()[0]
        except IndexError:
            return
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        metadata = SpecSaversMeta()
        promotion = response.xpath('//div[contains(@class, "product-page__ribbon")]/text()').extract()
        promotion = promotion[0].strip() if promotion else ''
        metadata['promotion'] = promotion

        item = loader.load_item()
        item['metadata'] = metadata
        yield item
