# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu as extract_price
from urlparse import urljoin as urljoin_rfc


class RasenschafDeSpider(BaseSpider):
    name = u'rasenschaf.de'
    allowed_domains = ['rasenschaf.de']
    start_urls = [
        'http://rasenschaf.de/startseite/?cur=0'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="navigation"]//a/@href').extract()[1:]:
            yield Request(urljoin_rfc(base_url, url + '?_artperpage=100'), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        category = ''.join(hxs.select('//*[@id="content"]/h1/text()').extract()).strip()
        for url in hxs.select('//*[@id="productList"]/li//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': category})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        options = hxs.select('//div[@id="detailsMain"]//input[@name="varselid[0]"]').extract()
        if options:
            for option_key in hxs.select('//*[@id="selectlist_0"]//li/a/@rel').extract():
                yield FormRequest.from_response(response,
                                                formnumber=3,
                                                formdata={'varselid[0]': option_key},
                                                callback=self.parse_option,
                                                meta={'url': response.url, 'category': response.meta['category']}
                                                )
        else:
            product_data = hxs.select('//div[@id="detailsMain"]').extract()
            if product_data:
                for product in self.parse_product_data(response.url, product_data[0], response.meta['category']):
                    yield product

    def parse_option(self, response):
        for product in self.parse_product_data(response.meta['url'], response.body, response.meta['category']):
            yield product

    def parse_product_data(self, url, product_data, category):
        hxs = HtmlXPathSelector(text=product_data)
        image_url = hxs.select('//div[@class="picture"]/a/img/@src').extract()
        product_identifier = hxs.select('//input[@name="aid"]/@value').extract()
        if not product_identifier:
            return
        product_identifier = product_identifier[0].strip()
        product_name = hxs.select('//*[@id="productTitle"]/span/text()').extract()[0].strip()
        brand = hxs.select('//img[@class="brandLogo"]/@alt').extract()
        brand = brand[0].strip() if brand else ''

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', image_url[0])
        price = hxs.select('//*[@id="productPrice"]/strong/text()').extract()[0]
        price = extract_price(price)
        sku = hxs.select('//*[@id="productArtnum"]/text()').extract()
        sku = sku[0].strip().replace('ArtNr.: ', '') if sku else ''
        product_loader.add_value('sku', sku)
        product_loader.add_value('price', price)
        product_loader.add_value('url', url)
        product_loader.add_value('brand', brand)
        product_loader.add_value('category', category)
        # if price < 3500:
        #     product_loader.add_value('shipping_cost', 2.99)
        # else:
        #     product_loader.add_value('shipping_cost', 0)
        product = product_loader.load_item()
        yield product
