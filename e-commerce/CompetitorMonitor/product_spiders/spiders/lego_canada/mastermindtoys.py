# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.utils import extract_price, fix_spaces

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class MastermindToysSpider(BaseSpider):
    name = "legocanada-mastermindtoys.com"
    allowed_domains = ["mastermindtoys.com"]
    start_urls = ["http://www.mastermindtoys.com/Lego-1.aspx"]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        next_url = hxs.select('//div[@class="mm_SearchPaging"]/a[img[contains(@src, "arrow_right")]]/@href').extract()
        if next_url:
            yield Request(urljoin(base_url, next_url[0]))

        product_urls = hxs.select('//div[@class="mm_SearchProduct"]/div[contains(@id, "ProductName")]/a/@href').extract()
        for url in product_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())

        name = hxs.select('//div[@class="mm_ProductDesc"]/h1/text()').extract()[0]
        name = fix_spaces(name)
        loader.add_value('name', name)
        loader.add_value('url', response.url)

        price = hxs.select('//span[contains(@id, "PriceLabel")]/text()').extract()
        price = extract_price(price[0]) if price else '0'
        loader.add_value('price', price)

        img_url = hxs.select('//div[contains(@class, "mm_ImgRotatorFadeDiv")]/img/@src').extract()
        if img_url:
            loader.add_value('image_url', urljoin(base_url, img_url[0]))

        loader.add_value('category', 'Lego')
        loader.add_value('brand', 'Lego')

        identifier = hxs.select('//a[contains(@id, "entryListAddtoCart_")]/@id').re('entryListAddtoCart_(.*)')
        if not identifier:
            identifier = hxs.select('//a[contains(@id, "addToWishList_")]/@id').re('addToWishList_(.*)')

        if not identifier:
            log.msg('ERROR >>> Product without identifier: ' + response.url)
            return

        loader.add_value('identifier', identifier[0])

        sku = hxs.select('//span[contains(@id, "manCode")]/text()').re('\d+')
        sku = sku[0] if sku else ''
        loader.add_value('sku', sku)

        
        if loader.get_output_value('price')<=0:
            loader.add_value('stock', 0)

        yield loader.load_item()
