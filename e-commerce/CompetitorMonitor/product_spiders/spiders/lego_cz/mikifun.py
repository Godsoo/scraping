# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class MikifunSpider(LegoMetadataBaseSpider):
    name = u'mikifun.cz'
    allowed_domains = ['www.mikifun.cz']
    start_urls = [
        u'http://www.mikifun.cz/cz/menu/1942/sortiment/hracky-dle-znacky/lego/',
    ]

    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # subcategories
        urls = hxs.select('//*[@id="content"]//p[@class="rozcestnik-odkaz"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)


    def parse_categories(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse pagination
        urls = hxs.select('//a[@class="pagination"]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)
        # products
        urls = hxs.select('//*[@id="content"]//h3/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)

        name = hxs.select('//*[@id="content"]//h3/text()').extract()[0].strip()
        price = hxs.select('//*[@id="content"]/div[1]/div[2]/p[4]/text()').extract()
        price = hxs.select('//*[@id="content"]/div[1]/div[2]/p[3]/text()').extract() if not price else price
        price = extract_price(price[0].strip().replace(u' K\u010d', '').replace(',', '.').replace(' ', ''))
        sku = hxs.select("//p[contains(text(),'Objednac') and contains(text(),'slo:')]/following::p[1]/text()").extract()[0]
        sku = sku[2:] if sku.startswith('22') else sku


        identifier = hxs.select('//div[@class="detail-koupit"]/form/@action').extract()[0]
        identifier = identifier.partition('volba=')[2]
        availability = hxs.select('//*[@id="content"]/div[1]/div[2]/div[1]/img/@alt').extract()[0].strip()
        category = hxs.select('//*[@id="content"]/h2/text()').extract()
        image_url = 'http://www.mikifun.cz' + hxs.select('//div[@id="content"]//a[@class="highslide"]/img/@src').extract()[0]

        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('image_url', image_url)
        loader.add_value('price', price)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('brand', 'LEGO')


        if category:
            loader.add_value('category', category[0])

        if availability != 'Skladem':
            loader.add_value('stock', 0)

        if int(price) <= 3000:
            loader.add_value('shipping_cost', 100)


        yield self.load_item_with_metadata(loader.load_item())
