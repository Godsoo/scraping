# -*- coding: utf-8 -*-
from decimal import Decimal
import re
import demjson
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc

from fragrancedirectitem import FragranceDirectMeta


class DebenhamscomSpider(BaseSpider):
    name = u'fragrancedirect-debenhams.com'
    allowed_domains = ['debenhams.com']
    start_urls = ['http://www.debenhams.com/beauty']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="subCategorycategories"]/ul/li/a/@href').extract()
        for category in categories:
            if '/beauty' not in category:
                continue
            yield Request(urljoin_rfc(base_url, category))

        sub_categories = hxs.select('//div[@class="cat_detail"]//a/@href').extract()
        for sub_category in sub_categories:
            if '/beauty' not in sub_category:
                continue
            yield Request(urljoin_rfc(base_url, sub_category))

        products = hxs.select('//tr[@class="item_container"]/td//input/@value').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        #pagination
        next_url = hxs.select('//a[contains(@onclick, "Next")]/@href').extract()
        if next_url:
            yield Request(urljoin_rfc(base_url, next_url[0]), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//h1[@class="catalog_link"]//text()').extract()
        url = response.url
        loader.add_value('url', urljoin_rfc(base_url, url))
        loader.add_value('name', name)
        image_url = hxs.select('//div[@id="pdp-large"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        categories = map(lambda x: x.strip(), hxs.select('//div[@class="breadcrumb_links"]//a/text()').extract())
        if categories:
            loader.add_value('category', categories)
        price = hxs.select('//div[@id="product_pricing"]//span[@class="now2"]/text()').extract()
        if not price:
            price = hxs.select('//span[contains(@class, "price-is")]/text()').extract()
        if not price:
            price = hxs.select('//div[@id="per_ml"]/p/text()').re('\d+.\d\d')

        price = ''.join(price)
        price = price.replace(u'\xa3', '')
        price = price.replace(u'&pound;', '')
        price = extract_price(price)

        identifier = hxs.select('//input[@id="tmProductParentSku"]/@value').extract()[0]

        loader.add_value('identifier', identifier)
        try:
	    sku = hxs.select('//div[@id="product-item-no"]/p/text()').extract()[0].replace('Item No.', '')
	except IndexError:
	    sku = ''
        loader.add_value('sku', sku)
        brand = hxs.select('//div[@id="product-brand-logo"]/a/@title').extract()
        brand = brand[0] if brand else ''
        loader.add_value('brand', brand)
        if price and price < 30:
            loader.add_value('shipping_cost', 3.99)
            loader.add_value('price', price + extract_price('3.99'))
        else:
            loader.add_value('shipping_cost', 0)
            loader.add_value('price', price)

        item = loader.load_item()

        promotional_data = hxs.select('//span[@class="price-save"]/text()').extract()
        metadata = FragranceDirectMeta()
        metadata['promotion'] = ' '.join(promotional_data[0].split()) if promotional_data else ''
        if item.get('price'):
            metadata['price_exc_vat'] = round((Decimal(item['price']) / Decimal('1.2')), 2)
        item['metadata'] = metadata

        body = ' '.join(response.body.split())

        options = re.search('var beauty_colours = (.*)config : {', body)
        if options:
            options = " ".join(options.group(1).split()) + "}"
            options = demjson.decode(options)
            options = options['colours']
        else:
            body = ''
            for line in response.body.split('\n'):
                if 'STOCK' not in line.upper():
                    body = body + '\n' + line
                    body = ' '.join(body.split())

            options = re.search('"sizes" : (.*), "config', body.strip())
            if options:
                options = demjson.decode(options.group(1).split(', "config"')[0])

        if options:
            for option in options:
                option_item = deepcopy(item)
                option_item['name'] = option_item['name'] +' ' + option['name']
                option_identifier = option['value']
                option_item['identifier'] = option_item['identifier'] + '-' + option_identifier
                option_item['price'] = extract_price(option['price'])
                if option_item.get('price'):
                    option_item['metadata']['price_exc_vat'] = round((Decimal(option_item['price']) / Decimal('1.2')), 2)
                if option_item['price'] and option_item['price'] < 30:
                    option_item['shipping_cost'] = extract_price('3.99')
                    option_item['price'] = option_item['price'] + option_item['shipping_cost']
                else:
                    option_item['shipping_cost'] = 0

                if option.get('out_of_stock', False):
                    option_item['stock'] = 0

                yield option_item
        else:
            yield item
