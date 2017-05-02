# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc


class DebenhamscomSpider(BaseSpider):
    name = u'debenhams.com'
    allowed_domains = ['www.debenhams.com']
    start_urls = [
        'http://www.debenhams.com/webapp/wcs/stores/servlet/Navigate?catalogId=10001&langId=-1&storeId=10701&lid=//productsuniverse/en_GB/product_online=Y/insearch=1/categories%3C{productsuniverse_18662}/categories%3C{productsuniverse_18662_72259}/brand_description%3E{nike}&mfv=brand_description;nike',
        'http://www.debenhams.com/women/shoes-boots/nike',
        'http://www.debenhams.com/men/shoes-boots/nike'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="item_container"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        #pagination
        for url in hxs.select('//*[@id="pagination"]//@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//h1[@class="catalog_link"]/text()').extract()[0].strip()
        url = response.url
        loader.add_value('url', urljoin_rfc(base_url, url))
        loader.add_value('name', name)
        image_url = hxs.select('//div[@id="pdp-large"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        category = hxs.select('//div[@class="breadcrumb_links"]//a/text()').extract()
        if category:
            loader.add_value('category', category[-1].strip())
        price = hxs.select('//div[@id="product_pricing"]//span[@class="now2"]/text()').extract()
        price = extract_price(price[0].replace(u'\xa3', ''))
        loader.add_value('price', price)
        identifier = hxs.select('//input[@id="tmProductParentSku"]/@value').extract()[0]

        loader.add_value('identifier', identifier)
        sku = hxs.select('//div[@id="product-item-no"]/p/text()').extract()[0].replace('Item No.', '')
        loader.add_value('sku', sku)
        loader.add_value('brand', 'Nike')
        if price < 30:
            loader.add_value('shipping_cost', 3.99)
        else:
            loader.add_value('shipping_cost', 0)
        yield loader.load_item()