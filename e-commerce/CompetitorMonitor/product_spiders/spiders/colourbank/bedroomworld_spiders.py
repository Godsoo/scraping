# -*- coding: utf-8 -*-
import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field
import json
import itertools

from scrapy import log

from product_spiders.spiders.bensons.bedroomworld_co_uk import BedroomworldSpider

from product_spiders.base_spiders.primary_spider import PrimarySpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class Meta(Item):
    net_price = Field()


class BedroomworldSpider(BedroomworldSpider):
    name = "colourbank-bedroomworld.co.uk"
    allowed_domains = ('bedroomworld.co.uk', )
    start_urls = ('http://www.bedroomworld.co.uk/', )

    shipping_costs = {'MATTRESS': 9.99,
                      'DIVAN BED': 19.99,
                      'BEDSTEAD': 9.99,
                      'FURNITURE': 9.99,
                      'PILLOWS': 3.99}

    def _start_requests(self):
        # yield Request('http://www.bedroomworld.co.uk/p/Slumberland_Harmony_800_Pocket_Divan_Set.htm', callback=self.parse_product)
        # yield Request('http://www.bedroomworld.co.uk/p/Kingston_Single_Folding_Bed.htm', callback=self.parse_product)
        yield Request('http://www.bedroomworld.co.uk/p/Baltic_Futon_Set.htm', callback=self.parse_product)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        self.log('Parsing %s' %response.url)
        self.log('Name %s' %hxs.select('//span[@itemprop="name"]/text()').extract())
        sku = response.xpath('//div[contains(@class, "order_code")]/text()').extract()
        sku = sku[0].split()[0] if sku else ''
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//span[@itemprop="name"]/text()')
        loader.add_xpath('price', '//span[starts-with(@id,"item_price_")]/text()')
        for category in hxs.select('//div[contains(@class, "ws-breadcrumb")]/a/text()').extract()[1:]:
            loader.add_value('category', category)
        img = hxs.select('//img[@id="imageMain"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        brand = response.xpath('//span[@itemprop="brand"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)

        names = {}
        for opt in hxs.select('//option[@mcode]'):
            mcode = opt.select('./@mcode').extract()[0]
            text = opt.select('normalize-space(./text())').extract()[0]
            names[mcode] = text
        
        loader.add_xpath('identifier', '//input[@id="item_details_product_id"]/@value')
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        loader.add_xpath('name', '//select[not(contains(@id, "quantity_"))]/option[@selected]/text()')
        product = loader.load_item()
        
        for key, shipping_cost in self.shipping_costs.iteritems():
            if key in product.get('category', "").upper():
                product['shipping_cost'] = shipping_cost
                break
        yield product
        
        url = 'http://www.bedroomworld.co.uk/ajax.get_exact_product.php?instart_disable_injection=true'
        sku = response.css('input#item_details_item_id::attr(value)').extract_first()
        attributes = response.xpath('//select/@id').re('(.+)_%s' %sku)
        attributes.remove('quantity')
        if not attributes:
            return
        options = []
        for attribute in attributes:
            options.append(response.xpath('//select[@id="%s_%s"]/option/@value' %(attribute, sku)).extract())
        variants = itertools.product(*options)
        for variant in variants:
            formdata = {'item_id': sku}
            for attribute, option in zip(attributes, variant):
                formdata['attributes[%s]' %attribute] = option
            yield FormRequest(url, 
                              self.parse_options, 
                              formdata=formdata,
                              meta={'item': Product(product)})

    def parse_options(self, response):
        json_data = json.loads(response.body)
        item = response.meta.get('item')
        prod_data = json_data['data']

        option_descriptions = prod_data['propertyType1']
        option_name = ''
        for option_desc in option_descriptions:
            if prod_data[option_desc].upper() not in item['name'].upper():
                option_name += ' ' + prod_data[option_desc]

        item['name'] += option_name
        item['identifier'] = prod_data['id']
        item['sku'] += '-' + prod_data['id']
        item['price'] = prod_data['ourprice']
        item['stock'] = prod_data['stockqty']

        yield item
