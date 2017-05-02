# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
import demjson
import re


class CreativekidstuffComSpider(BaseSpider):
    name = u'lego_usa_creativekidstuff.com'
    allowed_domains = ['creativekidstuff.com']
    start_urls = [
        'http://www.creativekidstuff.com/store/ck/service/items/4/3225?sort=popular&size=ALL&price=0,9999&view=100&page=1&summary=1&json=1'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        data = demjson.decode(response.body)

        product = None
        for product in data['itemList']:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            image_url = '//d39rqydp4iuyht.cloudfront.net/store/product/image/{}.gif'.format(product['id'])
            product_identifier = product['id']
            product_name = product['name']
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            product_loader.add_value('image_url', image_url)
            price = product['minPrice']
            sku = ''
            for match in re.finditer(r"([\d,\.]+)", product_name):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            product_loader.add_value('price', price)
            url = '/store/ck/item/' + str(product['id'])
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            yield product_loader.load_item()

        if product and product['dataPosition'] < data['numItems']:
            page = int(url_query_parameter(response.url, 'page')) + 1
            url = add_or_replace_parameter(response.url, 'page', str(page))
            yield Request(url)