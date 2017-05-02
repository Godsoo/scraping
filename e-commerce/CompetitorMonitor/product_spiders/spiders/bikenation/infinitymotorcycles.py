# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest, Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import itertools
import copy


class InfinitymotorcyclesSpider(BaseSpider):
    """
    WARNING!!!
    This spider uses cookiejar feature that requires scrapy v0.15
    That is why at the moment (17.07.2014) it is running on slave1 server
    which has scrapy 0.16 installed (default server has 0.14)
    """
    name = u'infinitymotorcycles.com'
    allowed_domains = ['www.infinitymotorcycles.com']
    start_urls = [
        'http://www.infinitymotorcycles.com'
    ]
    jar_counter = 0

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@id="megaInner"]//li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '/view-all'), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="productThumbLayout"]//li/a/@href').extract():
            self.jar_counter += 1
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          cookies={},
                          meta={'cookiejar': self.jar_counter})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        identifier = hxs.select('//*[@id="Form1"]//input[@name="productID"]/@value').extract()
        if not identifier:
            return
        loader.add_value('identifier', identifier[0])
        name = hxs.select('//*[@id="productTabulation"]/h1/text()').extract()[0].strip()
        url = response.url
        loader.add_value('url', urljoin_rfc(base_url, url))
        loader.add_value('name', name)
        image_url = hxs.select('//div[@class="swappertable"]//img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        category = hxs.select('//*[@id="breadcrumbs_inPage"]/ul/li[2]/a/text()').extract()
        if category:
            loader.add_value('category', category[0])
        price = hxs.select('//*[@id="pricingBlock"]//span[@class="infPrice"]/text()').extract()
        if not price:
            price = hxs.select('//*[@id="pricingBlock"]//span[@class="newprice"]/text()').extract()
        price = extract_price(price[0])
        loader.add_value('price', price)
        out_of_stock = hxs.select('//div[@class="buyButtonBlock"]/text()').extract()  # Currently Out of Stock
        if out_of_stock:
            loader.add_value('stock', 0)
        brand = hxs.select('//*[@id="productTabulation"]//a[@class="moreProductsLink"]/text()').extract()
        if brand:
            brand = brand[0].replace('View All', '').replace('Products', '').strip()
            loader.add_value('brand', brand)
        option_ids = hxs.select('//*[@id="Form1"]//select/@id').extract()
        variations_list = []
        for option_id in option_ids:
            option_values = hxs.select('//*[@id="Form1"]//select[@id="{}"]/option/@value'.format(option_id)).extract()
            option_names = hxs.select('//*[@id="Form1"]//select[@id="{}"]/option/text()'.format(option_id)).extract()
            options = []
            for option_value, option_name in zip(option_values, option_names):
                options.append({'code': option_value, 'name': option_name})
            variations_list.append(options)
        product = loader.load_item()
        response = response.replace(url=urljoin_rfc(base_url, '/cart/cart.asp'))
        yield FormRequest.from_response(response,
                                        formname="Form1",
                                        dont_filter=True,
                                        dont_click=True,
                                        callback=self.parse_shipping_price,
                                        meta={'product': product,
                                              'variations_list': variations_list,
                                              'cookiejar': response.meta['cookiejar']})

    def parse_shipping_price(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']
        shipping = hxs.select('//td[@class="carriage"][2]/text()').extract()
        if shipping:
            shipping = extract_price(shipping[0])
            product['shipping_cost'] = shipping
        variations_list = response.meta['variations_list']
        if not variations_list:
            yield product
        else:
            product_name = product['name']
            product_identifier = product['identifier']
            for variation in itertools.product(*variations_list):
                option_product = copy.deepcopy(product)
                name = product_name
                identifier = product_identifier
                for option in variation:
                    name += ', ' + option['name']
                    identifier += '-' + option['code']
                option_product['name'] = name
                option_product['identifier'] = identifier
                yield option_product