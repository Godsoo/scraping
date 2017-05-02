# -*- coding: utf-8 -*-
import os
import csv
import json
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
operator = 'O2'
channel = 'Direct'

class O2Spider(BaseSpider):
    name = 'telecoms_o2.co.uk'
    allowed_domains = ['o2.co.uk']
    start_urls = ('https://www.o2.co.uk',)

    products = []

    def start_requests(self):
        with open(os.path.join(HERE, 'o2_products.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for row in reader:
                yield Request(row.get('url'), callback=self.parse, meta={'device_name':row.get('device')})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        url = hxs.select('//div[@class="option" and h2/text()!="Pay & Go"]/div[@class="optionWrapper"]/div/a/@href').extract()
        if url:
            url = urljoin_rfc(get_base_url(response), url[0])
            yield Request(url, callback=self.parse_tariff, meta=response.meta)

    def parse_tariff(self, response):
        hxs = HtmlXPathSelector(response)

        device_name = response.meta['device_name']
        json_data = {}
        for line in response.body.split('\n'):
            if "var refreshTariff =" in line:
                json_data = json.loads(line.replace('; \r','').replace('var refreshTariff =', '').replace("\'", "").replace(';',''))


        tariffs = json_data['handset'][0]['plan']
        for tariff in tariffs:
            loader = ProductLoader(selector=tariff, item=Product())
            tariff_name = tariff['minutes'] + ' ' + tariff['texts'] + ' ' + tariff['data']
            duration = '24' #FIXME: Check if duration is always 24
            air_time_rate = tariff['airtimeRate']
            monthly_cost = tariff['handsetMonthlyRate']
            tariff_code = tariff['tariffId']
            price = tariff['upfrontCost']
            product_code = json_data['handset'][0]['id']
            loader.add_value('identifier', '-'.join((product_code, tariff_code, str(monthly_cost), str(price))))
            loader.add_value('name', response.meta['device_name'] + ' - ' + tariff_name)
            loader.add_value('url', response.url)
            loader.add_value('brand', json_data['handset'][0]['brand'])
            loader.add_value('price', price)
            image_url = 'https://www.o2.co.uk/shop/' + json_data['handset'][0]['image']
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url))

            product = loader.load_item()
            metadata = TelecomsMeta()
            metadata['device_name'] = response.meta['device_name']
            metadata['monthly_cost'] = monthly_cost + air_time_rate
            metadata['tariff_name'] = tariff_name
            metadata['contract_duration'] = duration
            metadata['operator'] = operator
            metadata['channel'] = channel
            is_3g = 'is4G=false' in response.url

            metadata['network_generation'] = tariff['network']#'3G' if is_3g else '4G'
            product['metadata'] = metadata

            yield product
