# -*- coding: utf-8 -*-
import os
import csv
import json
import cStringIO

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from telecomsitems import TelecomsMeta


HERE = os.path.abspath(os.path.dirname(__file__))

# account specific fields
channel = 'Indirect'
net_gen = '3G'

class CarphoneWarehouseSpider(BaseSpider):
    name = 'telecoms_carphonewarehouse.com'
    allowed_domains = ['carphonewarehouse.com']
    start_urls = ('http://www.carphonewarehouse.com',)
    operators = {'ORN': 'Orange',
                 'O2': 'O2',
                 'VOD': 'Vodafone',
                 'O2O': 'T-Mobile',
                 'EE': 'EE',
                 'TM': 'Talkmobile',}

    def start_requests(self):
        with open(os.path.join(HERE, 'carphonewarehouse_products.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for row in reader:
                if 'colourCode' in row.get('url'):
                    color = row.get('url').split('colourCode=')[-1]
                    device_id = row.get('url').split('/')[-2]
                else:
                    device_id = row.get('url').split('/')[-1]

                if color:
                    url = 'http://www.carphonewarehouse.com/solrSearch.do?facets={%22dt%22:%22pm%22,%22fp%22:%22paymtarifffinder%22,%22cc%22:%22'+color+'%22,%22mc%22:%22'+device_id+'%22,%22mo%22:%22PHONES%22,%22sort%22:%22rhr%20asc,pc%20asc,tp%20asc,nd%20asc%22,%22start%22:%221%22}'
                else:
                    url = 'http://www.carphonewarehouse.com/solrSearch.do?facets={%22dt%22:%22pm%22,%22fp%22:%22paymtarifffinder%22,%22mc%22:%22'+device_id+'%22,%22mo%22:%22PHONES%22,%22sort%22:%22rhr%20asc,pc%20asc,tp%20asc,nd%20asc%22,%22start%22:%221%22}'
                yield Request(url, callback=self.parse, meta={'device_name': row.get('device'),
                                                              'page': 1,
                                                              'color': color,
                                                              'device_id':device_id,
                                                              'device_url': row.get('url')})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        #name = hxs.select('//div[@class="cpwProdSummarySctn"]/h1/text()').extract()[0]
        #tariffs = hxs.select('//div[@id="monthlyRecomTab"]//table[@id="cpwPayMonthlyTariffTbl"]/tr[td[@class="cpwDataPhoneCost"]]')
        json_data = json.loads(response.body)
        tariffs = json_data['grouped']['sc']['groups']
        matches = json_data['grouped']['sc']['matches']
        start = json_data['grouped']['sc']['groups'][0]['doclist']['start']
        for item in tariffs:
            tariff = item['doclist']['docs'][0]
            loader = ProductLoader(selector=tariff, item=Product())
            minutes = tariff['dm'].replace('10000000', 'Unlimited')
            texts = tariff['dx'].replace('10000000', 'Unlimited')
            if tariff['da']>1000:
                data = str(tariff['da'] / 1024) + 'GB'
            else:
                data = str(tariff['da']) + 'MB'

            name = tariff['mn']
            tariff_name = ' '.join((minutes, texts, data))
            monthly_cost = tariff['tp']
            duration = tariff['cd']
            tariff_code = tariff['pi']
            loader.add_value('identifier', tariff_code)
            loader.add_value('name', response.meta['device_name'] + ' - ' + tariff_name)
            loader.add_value('url', response.meta.get('device_url'))
            loader.add_value('brand', name.split()[0])
            price = tariff['pc']
            loader.add_value('price', price)
            image_url = tariff['iu']
            if not image_url:
                image_url = hxs.select('//div[@class="cpwProdHeroImageSingle"]/img/@src').extract()

            if image_url:
                loader.add_value('image_url', image_url)

            product = loader.load_item()
            metadata = TelecomsMeta()
            metadata['device_name'] = response.meta['device_name']
            metadata['monthly_cost'] = monthly_cost
            metadata['tariff_name'] = tariff_name
            metadata['contract_duration'] = duration
            operator = tariff['np']
            metadata['operator'] = self.operators.get(operator, '')
            metadata['channel'] = channel
            metadata['network_generation'] = '4G' if tariff.get('fge', '')=='T' else '3G'
            product['metadata'] = metadata

            yield product
        if start < matches:
            color = response.meta.get('color')
            device_id = response.meta.get('device_id')
            page = response.meta.get('page') + 1
            url = 'http://www.carphonewarehouse.com/solrSearch.do?facets={%22dt%22:%22pm%22,%22fp%22:%22paymtarifffinder%22,%22cc%22:%22'+color+'%22,%22mc%22:%22'+device_id+'%22,%22mo%22:%22PHONES%22,%22sort%22:%22rhr%20asc,pc%20asc,tp%20asc,nd%20asc%22,%22start%22:%22'+str(page)+'%22}'
            yield Request(url, callback=self.parse, meta={'device_name': response.meta.get('device_name'),
                                                          'page': page,
                                                          'color': color,
                                                          'device_id':device_id,
                                                          'device_url': response.meta.get('device_url')})
