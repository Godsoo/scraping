# -*- coding: utf-8 -*-
"""
Customer: Blivakker
Website: http://www.bangerhead.no/
Extract all products including product options

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4620

"""

import os
import re 
import json
from copy import deepcopy
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.http import Request
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc


class BangerheadSpider(BaseSpider):
    name = 'blivakker-bangerhead.no'
    allowed_domains = ['bangerhead.no']
    start_urls = ['http://www.bangerhead.no/']

    def parse(self, response):
        categories = response.xpath('//section[@id="menu"]//a/@href').extract()
        categories += response.xpath('//div[@class="Produkttrad"]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))
            
        pages = response.xpath('//a/@href[contains(., "page=")]').extract()
        for page in pages:
            yield Request(response.urljoin(page))

        products = response.css('div.PT_Wrapper a::attr(href)').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        filters = response.xpath('//a[@rel="FVarum"]/@data-val').extract()
        filters = None
        if filters:
            filter_url = "http://www.bangerhead.no/shop?&artgrp=%s&funk=%s&f=FVarum!%s"
            artgrp = response.xpath('//form[@id="Frm_Filter"]/input[@name="artgrp"]/@value').extract()[0]
            funk = response.xpath('//form[@id="Frm_Filter"]/input[@name="funk"]/@value').extract()[0]
            for brand_filter in filters:
                yield Request(filter_url % (artgrp, funk, brand_filter))

        nextp = response.xpath('//div[@class="Artgrp_VisaFlerArtiklar"]/a[contains(text(), "Neste")]/@href').extract()
        if nextp:
            yield Request(response.urljoin(nextp[0]))

    def parse_product(self, response):
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        sku = response.xpath('//div[@id="productInfo"]//dt[@id="About"]/i/text()').extract()[-1].strip()
        if not sku:
            return
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)

        brand = response.xpath('//span[@id="varum"]/text()').extract_first()
        if not brand:
            brand = response.xpath('//span[@class="brand"]/text()').extract()
        loader.add_value('brand', brand)

        name = response.xpath('//b[@itemprop="name"]/text()').extract_first()
        loader.add_value('name', name)
        loader.add_value('url', response.url)

        price = response.xpath('//span[@id="PrisFalt"]/meta[@itemprop="price"]/@content').extract_first()
        price_before = response.css('.price-rek span#rekPris::text').extract_first()
        if price_before and Decimal(price_before) > Decimal(price):
            sales_price = price
        else:
            sales_price = None        
        loader.add_value('price', price)

        image_url = response.css('img#produktbild::attr(src)').extract_first()
        if not image_url:
            image_url = response.xpath('//div[@class="product-image"]/img/@src').extract_first()
        image_url = response.urljoin(image_url) if image_url else ''
        loader.add_value('image_url', image_url)

        categories = response.css('span.breadcrumb a::text').extract()[-3:]
        loader.add_value('category', categories)

        out_stock = response.xpath(u'//div[@class="artikel_i_lager"]//span[contains(text(), "Slutt på lager")]')
        if out_stock:
            loader.add_value('stock', 0)
        item = loader.load_item()
        if sales_price:
            item['metadata'] = {'SalesPrice': extract_price(sales_price)}
 
        options = response.css('div.WrapVar')
        if options:
            if sales_price:
                self.logger.warning('Sales price and options on the %s' %response.url)
            for option in options:
                option_item = deepcopy(item)
                identifier = option.xpath('.//@id').re('VarList(.*)')[0]
                option_item['identifier'] += '-' + identifier
                price = option.css('div.PT_Pris::text').extract()
                if price:
                    option_item['price'] = extract_price(price[0])
                name = option.xpath('@variant-name').extract_first()
                if name:
                    option_item['name'] += ' ' + name
                image_url = response.xpath('//img[contains(@src, "'+identifier+'")]/@src').extract()
                if image_url:
                    option_item['image_url'] = urljoin_rfc(get_base_url(response), image_url[0].split('img=')[-1]) if image_url else '' 

                stock_data = re.findall('var rubrikartikel = (.*);', response.body)
                if stock_data:
                    stock_data = json.loads(stock_data[0])
                    for stock in stock_data['varianter']:
                        if stock['artnr'] == identifier:
                            option_item['stock'] = stock['saldo']
                            break
                yield option_item
        else:
            yield item

