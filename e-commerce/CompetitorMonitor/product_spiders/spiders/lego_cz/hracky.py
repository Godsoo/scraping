# -*- coding: utf-8 -*-
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
import re
from product_spiders.utils import extract_price_eu as extract_price
from urlparse import urljoin as urljoin_rfc
from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class HrackyCzSpider(LegoMetadataBaseSpider):
    name = u'hracky.cz'
    allowed_domains = ['hracky.cz', 'hracky.alza.cz']
    start_urls = [
        u'http://hracky.alza.cz/lego/v2291.htm',
    ]
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse pagination
        urls = hxs.select('//*[@id="pagerbottom"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)
        # products
        urls = hxs.select('//*[@id="boxes"]//div[@class="fb"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        image_url = hxs.select('//*[@id="imgMain"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//*[@id="prices"]//span[@class="bigPrice"]/text()').extract()
        if not price:
            price = hxs.select('//*[@id="prices"]/tr[1]/td[2]/span/text()').extract()
        if price:
            price = extract_price(price[0].strip().replace(' ', '').replace(u'\xa0', ''))
        loader.add_value('price', price)
        category = hxs.select('//div[@class="breadCrupmps"]//a/text()').extract()
        if category:
            loader.add_value('category', category[-2])
        sku = ''
        for match in re.finditer(r"([\d,\.]+)", name):
            if len(match.group()) > len(sku):
                sku = match.group()
        loader.add_value('sku', sku)
        identifier = hxs.select('//*[@id="surveyObjectId"]/@value').extract()[0]
        loader.add_value('identifier', identifier.strip())
        loader.add_value('brand', 'LEGO')
        yield self.load_item_with_metadata(loader.load_item())
