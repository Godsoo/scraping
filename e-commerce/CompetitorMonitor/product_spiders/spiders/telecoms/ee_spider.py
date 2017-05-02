# -*- coding: utf-8 -*-
import os
import csv
import json
import cStringIO

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url

from telecomsitems import TelecomsMeta


HERE = os.path.abspath(os.path.dirname(__file__))

# account specific fields
channel = 'Direct'

class EESpider(BaseSpider):
    name = 'telecoms_ee.co.uk'
    allowed_domains = ['ee.co.uk']
    start_urls = ('http://shop.ee.co.uk',)

    products = []

    def start_requests(self):
        with open(os.path.join(HERE, 'ee_products.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for row in reader:
                yield Request(row.get('url'), dont_filter=True, callback=self.parse, meta={'device_name':row.get('device')})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        collected_devices = []
        device_name = response.meta['device_name']
        name = hxs.select('//h1/text()').extract()[0]

        tariffs = hxs.select('//li[contains(@class, "ee-plan-row ")]')

        for tariff in tariffs:
            data = ''.join(tariff.select('div/div[@class="cell data"]/text()').extract()).strip().upper()
            min_text = ' '.join(''.join(tariff.select('div/div[@class="cell minutes-texts"]/text()').extract()).split())
            tariff_name = data+ ' ' + min_text
            monthly_cost = tariff.select('div/div[@class="cell mrc"]/text()').extract()[-1].strip()
            net_gen = '4G'
            duration = '24'
            prod_cod_1 = tariff.select('div/div/form/p/input[@name="productCode1"]/@value').extract()
            if not prod_cod_1:
                continue

            prod_cod_2 = tariff.select('div/div/form/p/input[@name="productCode2"]/@value').extract()
            tariff_code = prod_cod_1[0] + '-' + prod_cod_2[0]
            price = ''.join(tariff.select('div/div[@class="cell upfront-cost"]/text()').extract()).strip()
            operator =  'EE'

            loader = ProductLoader(selector=tariff, item=Product())
            loader.add_value('identifier', tariff_code)
            loader.add_value('name', response.meta['device_name'] + ' - ' + tariff_name)
            loader.add_value('url', response.url)
            loader.add_value('brand', name.split()[0])
            loader.add_value('price', price)
            image_url = hxs.select('//div[@class="product-image"]/span//img/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

            product = loader.load_item()
            metadata = TelecomsMeta()
            metadata['device_name'] = response.meta['device_name']
            metadata['monthly_cost'] = monthly_cost
            metadata['tariff_name'] = tariff_name
            metadata['contract_duration'] = duration
            metadata['operator'] = operator
            metadata['channel'] = channel
            metadata['network_generation'] = '4G' if '4G' in net_gen else '3G'
            product['metadata'] = metadata

            yield product
