# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc


class OfficeCoUkSpider(BaseSpider):
    name = u'office.co.uk'
    allowed_domains = ['www.office.co.uk']
    start_urls = [
        'http://www.office.co.uk/view/category/office_catalog/2?pageSize=9999&BRAND=Nike',
        'http://www.office.co.uk/view/category/office_catalog/1?pageSize=9999&BRAND=Nike',
        'http://www.office.co.uk/view/category/office_catalog/4?pageSize=9999&BRAND=Nike'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="productList_info"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//*[@id="breadcrumbs"]/span//a/text()').extract()[-1].strip()
        colour = hxs.select('//h2[contains(@class, "productColour")]/text()').extract()
        if colour:
            name += " " + colour[0]
        url = response.url
        loader.add_value('url', urljoin_rfc(base_url, url))
        loader.add_value('name', name)
        image_url = hxs.select('//*[@id="ql_product_thumbnails"]/ul/li[1]/img/@picture').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        category = hxs.select('//*[@id="breadcrumbs"]/span//a/text()').extract()
        if category:
            loader.add_value('category', category[-2].strip())
        price = hxs.select('//div[@id="now_price"]/text()').extract()[0].strip().replace(u'\xa3', '')
        price_dec = hxs.select('//div[@id="now_price"]/sup/text()').extract()[0]
        price = extract_price(price + price_dec)
        loader.add_value('price', price)
        identifier = hxs.select('//input[@id="productCodeId"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('brand', 'Nike')
        free_delivery = False
        delivery = hxs.select('//div[@class="productDetail_brandLogos"]//img/@src').extract()
        for d in delivery:
            if '/styles/images/freeDeliveryTag.png?' in d:
                free_delivery = True
                break
        if not free_delivery:
            loader.add_value('shipping_cost', 3.50)
        else:
            loader.add_value('shipping_cost', 0)
        yield loader.load_item()