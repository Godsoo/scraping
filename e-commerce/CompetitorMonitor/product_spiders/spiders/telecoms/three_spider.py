# -*- coding: utf-8 -*-
import os
import re
import csv
import cStringIO

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from telecomsitems import TelecomsMeta


HERE = os.path.abspath(os.path.dirname(__file__))

# account specific fields
operator = 'Three'
channel = 'Direct'
net_gen = '3G'

class ThreeSpider(BaseSpider):
    name = 'telecoms_three.co.uk'
    allowed_domains = ['three.co.uk']
    start_urls = ('http://store.three.co.uk',)

    products = []

    def start_requests(self):
        with open(os.path.join(HERE, 'three_products.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for row in reader:
                yield Request(row.get('url'), callback=self.parse, meta={'device_name':row.get('device')})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        name = ' '.join(hxs.select('//div[contains(@class, "deviceTitle")]/text()').extract()).strip()
        tariffs = hxs.select('//form[@id="command" and div[contains(@class, "planName")]/text()!="Pay As You Go."]')
        for tariff in tariffs:
            loader = ProductLoader(selector=tariff, item=Product())
            tariff_name = tariff.select('div[contains(@class, "planName")]/text()').extract()[0]
            monthly_cost = tariff.select('div//div[contains(@class, "priceColumn")]/div[contains(@class, "price")]/text()').extract()[0]
            duration = tariff.select('div//li[contains(text(), "months")]/text()').extract()[0].split(u' ')[0].replace(u'\xa0months', '')
            product_code = tariff.select('input[@name="productCode"]/@value').extract()[0]
            tariff_code = tariff.select('input[@name="packageCode"]/@value').extract()[0]
            loader.add_value('identifier', product_code + '-' + tariff_code.replace('ContractD', '') + '-' + str(duration))
            loader.add_value('name', response.meta['device_name'] + ' - ' + tariff_name)
            loader.add_value('url', response.url)
            loader.add_value('brand', name.split()[0])
            price = tariff.select('div//div[contains(@class, "upfrontPrice")]/span/text()').extract()[0]
            loader.add_value('price', price)
            image_url = hxs.select('//div[@class="devicePicturePanel"]/div/a/img/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

            product = loader.load_item()
            metadata = TelecomsMeta()
            metadata['device_name'] = response.meta['device_name']
            metadata['monthly_cost'] = monthly_cost.replace(u'\u00a3', '')
            metadata['tariff_name'] = tariff_name
            metadata['contract_duration'] = duration
            metadata['operator'] = operator
            metadata['channel'] = channel
            metadata['network_generation'] = net_gen
            product['metadata'] = metadata

            yield product

        tariffs = hxs.select('//li[@class="visible"]')
        if tariffs:
            name = hxs.select('//h1[@class="main-title section"]/text()').extract()[0]
            for tariff in tariffs:
                mem_size = tariff.select('@data-memory').extract()[0]
                colour = tariff.select('@data-colour').extract()[0]
                if mem_size in response.meta['device_name'] and colour in response.url.replace('_', ' '):
                    loader = ProductLoader(selector=tariff, item=Product())
                    tariff_name = tariff.select('@data-planname').extract()[0]
                    monthly_cost = tariff.select('@data-monthly-cost').extract()[0]
                    duration = tariff.select('div/div/p[contains(text(), "month contract")]/em/text()').extract()[0]
                    tariff_code = re.search('ContractD(\w+)', tariff.select('div/div[@class="links"]/a[@class="chevron-link cta"]/@href').extract()[0]).group(1)
                    loader.add_value('identifier', tariff_code + '-' + str(duration))
                    loader.add_value('name', response.meta['device_name'] + ' - ' + tariff_name)
                    loader.add_value('url', response.url)
                    loader.add_value('brand', name.split()[0])
                    price =  tariff.select('@data-upfront-cost').extract()[0]
                    loader.add_value('price', price)
                    image_url = hxs.select('//a[contains(@class, "product-imag") and @data-colour="'+colour+'"]/img/@src').extract()
                    if image_url:
                        loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

                    product = loader.load_item()
                    metadata = TelecomsMeta()
                    metadata['device_name'] = response.meta['device_name']
                    metadata['monthly_cost'] = monthly_cost
                    metadata['tariff_name'] = tariff_name
                    metadata['contract_duration'] = duration
                    metadata['operator'] = operator
                    metadata['channel'] = channel
                    metadata['network_generation'] = net_gen
                    product['metadata'] = metadata
  
                    yield product
