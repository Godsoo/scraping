# -*- coding: utf-8 -*-
import os
import re
import csv
import urlparse
import cStringIO
import demjson

from decimal import Decimal

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
operator = 'Vodafone'
channel = 'Direct'

class VodafoneSpider(VodafoneBaseSpider):
    name = 'vodafone-vodafone.de'
    allowed_domains = ['vodafone.de']
    start_urls = ('http://www.vodafone.de/privat/handys-tablets-tarife/smartphone-tarife.html',)

    products = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        phones = re.search('window.phones=(.*);', response.body)
        collected = []
        if phones:
            phones = phones.group(1)
            phones = demjson.decode(phones, encoding='ISO-8859-1' )

            rates = re.search('window.rates=(.*);', response.body).group(1)
            rates = demjson.decode(rates, encoding='utf8' )

            discounts = re.search('window.discounts=(.*);', response.body).group(1)
            discounts = demjson.decode(discounts, encoding='ISO-8859-1')

            services = re.search('window.services=(.*);', response.body).group(1)
            services = demjson.decode(services, encoding='ISO-8859-1')

            propositions = re.search('window.propositions=(.*);', response.body).group(1)
            propositions = demjson.decode(propositions, encoding='ISO-8859-1')

        for phone_id, phone in phones.iteritems():
            if 'iphone 6' in phone['name'].lower() or 'samsung galaxy s5' in phone['name'].lower() and 'samsung galaxy s5 mini' not in phone['name'].lower():
                normalized_name = self.get_normalized_name(phone['name'])
                if normalized_name not in collected:
                    collected.append(normalized_name)
                else:
                    continue

                image_url =  urljoin_rfc('http://shop.vodafone.de/', phone['imageLarge'])
         
                phone_skus = [k for k, d in phone.iteritems() if k.startswith('sku')]
                for phone_sku in phone_skus:
                    # phone price
                    phone_price = phone[phone_sku]['e']

                    for prod_id, rate in rates.iteritems():
                        tariff_name = rate['label']
                        rate_phone = rate['subsku'].get(phone_sku, None)

                        if rate_phone:
                            total_discount = 0
                            # Use the last discount
                            for discount_sku in rate_phone['discounts'][-1:]:
                                discount = discounts[discount_sku]
                                if discounts[discount_sku]['DurationInMonths'] == '24':
                                    total_discount = total_discount + extract_price(discount['Value'].get(phone_sku, '0'))


                            default_discount = discounts.get(rate_phone['defaultDiscount'], None)
                            if default_discount and rate_phone['defaultDiscount'] not in rate_phone['discounts']:
                                total_discount = total_discount + extract_price(default_discount['Value'].get(phone_sku, '0'))

                            phone_services = propositions[phone[phone_sku]['p']][phone_sku]['services'].keys()


                            total_services = 0
                            for phone_service in phone_services:
                                value = services[phone_service]['Value']
                                if '-' in value and services[phone_service]['duration_in_months']=='24':
                                    total_services += Decimal(value)
                            
                            monthly_cost = extract_price(rate_phone['monthlyChargest']) + total_services - total_discount
 

                            loader = ProductLoader(item=Product(), response=response)
                            duration = '24'
 
                            loader.add_value('identifier', phone[phone_sku]['p']+'-'+rate['propId'])
                            loader.add_value('name', normalized_name  + ' - ' + tariff_name)
                            loader.add_value('url', response.url)
                            loader.add_value('brand', phone['name'].split()[0])
                            loader.add_value('price', phone_price)
                            loader.add_value('image_url', image_url)

                            promotional_text = hxs.select('//div[@sku="'+rate['propId']+'"]//div[contains(@class,"aktion")]/div[contains(@class, "hook")]/text()').extract()
                            promotional_text = ', '.join(map(lambda x: x.strip(), promotional_text))
             
                            product = loader.load_item()
                            metadata = VodafoneMeta()
                            metadata['device_name'] = phone['name']
                            metadata['monthly_cost'] = monthly_cost
                            metadata['tariff_name'] = tariff_name
                            metadata['contract_duration'] = duration
                            metadata['operator'] = operator
                            metadata['channel'] = channel
                            metadata['promotional_text'] = promotional_text
                            is_4g = '4G|LTE' in ''.join(hxs.select('//div[@sku="'+rate['propId']+'"]//div[@class="features"]/div/text()').extract()).strip().upper()
                            metadata['network_generation'] = '4G' if is_4g else '3G'
                            product['metadata'] = metadata

                            yield product
