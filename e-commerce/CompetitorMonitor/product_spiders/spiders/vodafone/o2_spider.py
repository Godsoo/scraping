# -*- coding: utf-8 -*-
import os
import re
import csv
import urlparse
import cStringIO
import demjson

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from vodafoneitems import VodafoneMeta

from scrapy import log

from vodafone_basespider import VodafoneBaseSpider

# account specific fields
operator = 'O2'
channel = 'Direct'

class O2Spider(VodafoneBaseSpider):
    name = 'vodafone-o2online.de'
    allowed_domains = ['o2online.de']
    start_urls = ('http://www.o2online.de/handy/iphone6/',
                  'http://www.o2online.de/handy/samsung-galaxy-s5/',
                  'http://www.o2online.de/handy/iphone6plus/')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        clean_html = ''
        for line in response.body.split('\n'):
            if not line.strip().startswith('//'):
                clean_html += line.strip() + ' '

        devices = re.search('var config = { devices: (.*?), tariffs: ', clean_html).group(1)
        devices = demjson.decode(devices, encoding='ISO-8859-1')

        tariffs = re.search('}, tariffs: (.*?)};', clean_html).group(1)
        tariffs = demjson.decode(tariffs, encoding='ISO-8859-1')

        uni = False
        if tariffs.get('low', None):
            tariffs = tariffs.get('low', None)
        else:
            tariffs = tariffs.get('uni', None)
            uni = True

        device_prices = tariffs.pop('devicePriceOnce')
        for tariff_id, tariff in tariffs.iteritems():
            for device_id, device in devices.iteritems():
                for device_color_id, device_color in device.iteritems():
                    for device_size_id, device_size in device_color.iteritems():
                        try:
                            device_iddentifier = device_color[device_size_id].get('deviceID', None)
                        except:
                            device_iddentifier = device_color.get('deviceID', None)
                            

                        if not device_iddentifier:
                            continue

                        device_name = re.sub('<[^<]+?>', '', device_color['name'])
                        if uni:
                            price = device_prices
                            monthly_cost = tariff['uni']['price']
                        else:
                            monthly_cost = tariff[device_size_id]['price']
                            device_name = device_name + ' ' + device_size_id
                            price = device_prices[device_size_id]

                        tariff_name = re.sub('<[^<]+?>', '', tariff['name'])
                        identifier = device_iddentifier+'-'+tariff_id

                        normalized_name = self.get_normalized_name(device_name)
                        loader = ProductLoader(item=Product(), response=response)
                        duration = '24'
                        loader.add_value('identifier', identifier)
                        loader.add_value('name', normalized_name  + ' - ' + tariff_name)
                        loader.add_value('url', response.url)
                        loader.add_value('brand', device_name.split()[0])
                        loader.add_value('price', price)
                        image_url = device_color['thumbLink']
                        loader.add_value('image_url', image_url)
        
                        product = loader.load_item()
                        metadata = VodafoneMeta()
                        metadata['device_name'] = device_name
                        metadata['monthly_cost'] = monthly_cost
                        metadata['tariff_name'] = tariff_name
                        metadata['contract_duration'] = duration
                        metadata['operator'] = operator
                        metadata['channel'] = channel
                        metadata['network_generation'] = '4G'
     
                        product['metadata'] = metadata

                        yield product
