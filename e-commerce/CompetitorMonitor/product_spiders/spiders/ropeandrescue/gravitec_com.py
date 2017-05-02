import re
import json
import logging

from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from scrapy import log

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class GravitecSpider(BaseSpider):
    name = 'gravitec.com'
    allowed_domains = ['gravitec.com']
    start_urls = ('http://www.gravitec.com/equipment/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for link in hxs.select('//div[@id="product-categories"]//h3/a'):
            url = urljoin_rfc(get_base_url(response), link.select('@href').extract()[0])
            # NOTE: viewall to skip pagination
            yield Request(add_or_replace_parameter(url, 'limit', '100'),
                          meta={'category': link.select('text()').extract()[0]},
                          callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//h2[@class="product-name"]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0]
        product_sku = hxs.select('//div[@class="product-name"]/h4/text()').re(r'Item #([\w-]+)')[0]
        product_image = hxs.select('//img[@class="mainImg"]/@src').extract()[0]

        product_config_reg = re.search('new Product.Config\((\{.*\})\);', response.body)
        if product_config_reg:
            conf = product_config_reg.group(1).split("});")[0]
            if not conf.endswith("}"):
                conf = conf + "}"
            products = json.loads(conf)
            for identifier, product in products['childProducts'].items():
                product_loader = ProductLoader(item=Product(), response=response)
                if identifier:
                    product_loader.add_value('identifier', product_sku + '-' + identifier)
                else:
                    product_loader.add_value('identifier', product_sku)
                product_loader.add_value('price', product[u'finalPrice'])
                option_name = product_name
                for attr_id, attribute in products[u'attributes'].items():
                    for option in attribute['options']:
                        if identifier in option['products']:
                            option_name += ' ' + option['label']
                product_loader.add_value('name', option_name)
                product_loader.add_value('sku', product_sku)
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', response.meta.get('category'))
                product_loader.add_value('image_url', product_image)

                yield product_loader.load_item()
        else:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('name', product_name)
            product_loader.add_value('sku', product_sku)
            product_loader.add_value('identifier', product_sku)
            product_loader.add_value('url', response.url)
            product_loader.add_value('category', response.meta.get('category'))
            product_loader.add_value('image_url', product_image)
            price = hxs.select('//div[@class="price-box"]//span[@class="price"]/text()').extract()
            price = price[0] if price else 0
            product_loader.add_value('price', price)

            yield product_loader.load_item()
