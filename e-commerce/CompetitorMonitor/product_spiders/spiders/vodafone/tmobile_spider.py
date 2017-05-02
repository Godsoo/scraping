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

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from phantomjs import PhantomJS

# account specific fields
operator = 'T-Mobile'
channel = 'Direct'

class VodafoneSpider(VodafoneBaseSpider):
    name = 'vodafone-t-mobile.de'
    allowed_domains = ['vodafone.co.uk']
    start_urls = ('https://www.t-mobile.de/apple-iphone/iphone-6/0,26907,28800-_,00.html',
                  'https://www.t-mobile.de/apple-iphone/iphone-6-plus/0,26908,28801-_,00.html?WT.svl=100',
                  'https://www.t-mobile.de/samsung-galaxy/samsung-galaxy-s5-lte/0,27026,28852-_,00.html?WT.svl=100')


    def __init__(self, *args, **kwargs):
        super(VodafoneSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        # Browser
        self.log('>>> BROWSER: Open browser')
        self._browser = PhantomJS()
        self.log('>>> BROWSER: OK')

    def spider_closed(self, spider):
        self._browser.close()

    def parse(self, response):
        base_url = get_base_url(response)
        selected_option_id = response.meta.get('option_id', None)
        self._browser.get(response.url)

        container = self._browser.driver.find_element_by_xpath('//div[@class="chosen-container chosen-container-single chosen-container-single-nosearch"]')
        container.click()

        hxs = HtmlXPathSelector(text=self._browser.driver.page_source)

        if not selected_option_id:
            options = hxs.select('//ul[@class="chosen-results"]/li/@data-option-array-index').extract()
            for option_id in options:
                yield Request(response.url, dont_filter=True, meta={'option_id': option_id})
            return


        option = self._browser.driver.find_element_by_xpath('//ul[@class="chosen-results"]/li[@data-option-array-index="'+selected_option_id+'"]')
        option.click()
        
        hxs = HtmlXPathSelector(text=self._browser.driver.page_source)
        tariffs = hxs.select('//li[contains(@class, "rate-element")]')

        device_identifier = re.search('0,(.*?)-_', response.url).group(1)

        for tariff in tariffs:

            loader = ProductLoader(item=Product(), response=response)
            duration = '24'
 
            identifier = tariff.select('@data-shop-id').extract()
            loader.add_value('identifier',  device_identifier+'-'+selected_option_id+'-'+identifier[0])
            phone_name = ' '.join(tariff.select('.//div[@class="configuration-output"]//p[not(span)]//text()').extract())
            tariff_name= ' '.join(tariff.select('.//div[@class="heading-2"]/span[@class="title-1" or @class="title-2"]//text()').extract())
            phone_price = ''.join(tariff.select('.//div[@class="configuration-output"]//p/span//text()').extract()).replace(',','.')
            image_url = hxs.select('//div[@id="device-image-slider"]//li/img/@src').extract()
            if image_url:
               image_url = urljoin_rfc(base_url, image_url[0])
            monthly_cost = ''.join(tariff.select('.//p[@class="price monthly-price"]/span//text()').extract()).replace(',', '.')
          
            normalized_name = self.get_normalized_name(phone_name)
            loader.add_value('name', normalized_name  + ' - ' + tariff_name)
            loader.add_value('url', response.url)
            loader.add_value('brand', phone_name.split()[0])
            loader.add_value('price', phone_price)
            loader.add_value('image_url', image_url)
  
            product = loader.load_item()
            metadata = VodafoneMeta()
            metadata['device_name'] = phone_name
            metadata['monthly_cost'] = re.search('(\d+.\d+)', monthly_cost).group(1)
            metadata['tariff_name'] = tariff_name
            metadata['contract_duration'] = duration
            metadata['operator'] = operator
            metadata['channel'] = channel
            metadata['promotional_text'] = ''
            metadata['network_generation'] = '4G'
            product['metadata'] = metadata
      
            yield product
