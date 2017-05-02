# -*- coding: utf-8 -*-
import os
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
channel = 'Indirect'

class Phones4uSpider(BaseSpider):
    name = 'telecoms_phones4u.co.uk'
    allowed_domains = ['phones4u.co.uk']
    start_urls = ('http://www.phones4u.co.uk',)

    products = []

    def start_requests(self):
        with open(os.path.join(HERE, 'phones4u_products.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for row in reader:
                yield Request(row.get('url'), callback=self.parse, meta={'device_name':row.get('device')})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        meta = response.meta
        operators = hxs.select('//label/a[contains(@href, "networkName")]')
        for operator in operators:
            operator_url = urljoin_rfc(base_url, operator.select('@href').extract()[0])
            net_3g = operator_url+'&generation=3G'
            net_4g = operator_url+'&generation=4G'
            meta['operator'] = operator.select('text()').extract()[0]
            yield Request(net_4g, callback=self.parse_operator, meta=meta)
            yield Request(net_3g, callback=self.parse_operator, meta=meta)
            net_3g = operator_url+'&tariffDataSpeed=3G'
            net_4g = operator_url+'&tariffDataSpeed=4G'
            yield Request(net_4g, callback=self.parse_operator, meta=meta)
            yield Request(net_3g, callback=self.parse_operator, meta=meta)

    def parse_operator(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        tariffs = hxs.select('//table[contains(@class, "price-plans")]/tr[td[contains(@class, "col")]]')
        name = ' '.join(hxs.select('//h3[@class="handset-name"]/text()').extract()[0].split())
        for tariff in tariffs:
            loader = ProductLoader(selector=tariff, item=Product())
            tariff_name = ' '.join(' '.join(tariff.select('td[@class="col1" or @class="col2" or @class="col3" or @class="col4"]/child::*/text()').extract()).split())
            monthly_cost =tariff.select('td[contains(@class, "col7")]/h4/text()').extract()[0]
            duration = u'24'
            #product_code = tariff.select('input[@name="productCode"]/@value').extract()[0]
            net_gen = '4G' if 'generation=4G' in response.url else '3G'
            tariff_code = tariff.select('td[contains(@class, "col7")]/div/form/input[@name="packageCode"]/@value').extract()[0]
            loader.add_value('identifier', tariff_code)
            loader.add_value('name', response.meta['device_name'] + ' - ' + tariff_name)
            loader.add_value('url', response.url)
            loader.add_value('brand', name.split()[0])
            price = tariff.select('td[contains(@class, "col6")]/h4/text()').extract()
            loader.add_value('price', price)
            image_url = hxs.select('//span[@class="handset-image"]/img/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

            product = loader.load_item()
            metadata = TelecomsMeta()
            metadata['device_name'] = meta['device_name']
            metadata['monthly_cost'] = monthly_cost.replace(u'\xa3', '')
            metadata['tariff_name'] = tariff_name
            metadata['contract_duration'] = duration
            metadata['operator'] = meta['operator']
            metadata['channel'] = channel
            metadata['network_generation'] = net_gen
            product['metadata'] = metadata

            yield product

        next = hxs.select('//a[i[contains(@class, "i-right-arrow-white")] and contains(@href, "page")]/@href').extract()
        if next:
            url = urljoin_rfc(get_base_url(response), next[0])
            yield Request(url, callback=self.parse_operator, meta=meta)
