# -*- coding: utf-8 -*-
import os
import csv
import urlparse
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
operator = 'Vodafone'
channel = 'Direct'

class VodafoneSpider(BaseSpider):
    name = 'telecoms_vodafone.co.uk'
    allowed_domains = ['vodafone.co.uk']
    start_urls = ('http://shop.vodafone.co.uk',)

    products = []

    def start_requests(self):
        with open(os.path.join(HERE, 'vodafone_products.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for row in reader:
                yield Request(row.get('url'), callback=self.parse, meta={'device_name':row.get('device')})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        url = hxs.select('//div[@class="ChoosePlan"]/a/@href').extract()
        name = hxs.select('//h1[@class="DetailPetrolTitle"]/text()').extract()
        if url:
            image_url = hxs.select('//div[@class="DetailsImgCont"]/a/img/@src').extract()
            image_url = image_url[0] if image_url else ''
            meta = response.meta
            meta['image_url'] = image_url
            meta['site_name'] = name[0] if name else ''
            yield Request(urljoin_rfc(get_base_url(response), url[0]), callback=self.parse_net_gen, meta=meta)

    def parse_net_gen(self, response):
        hxs = HtmlXPathSelector(response)
        url_3g = response.url.replace('compatiblePlanListView.jsp?', 'compatiblePlanListView.jsp?initialFilters=flt_3gplans&')
        url_3g = url_3g.replace('from=phoneSku&', 'from=phoneSku&initialFilters=flt_3gplans&')
        yield Request(url_3g, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        tariffs = hxs.select('//div[contains(@class, "planList") and contains(@class, "flt_personaluse")]')
        for tariff in tariffs:
            loader = ProductLoader(selector=tariff, item=Product())
            minutes = ' '.join(''.join(tariff.select('ul/li[@class="details minutes"]/p//text()').extract()).split())
            text = ' '.join(''.join(tariff.select('ul/li[@class="details texts"]/p//text()').extract()).split())
            mobile_internet = ' '.join(''.join(tariff.select('ul/li[@class="details MobIntertxt"]/p//text()').extract()).split())
            duration = ' '.join(''.join(tariff.select('ul/li[@class="details contractType"]/p//text()').extract()).split())

            tariff_name = ' '.join((minutes, text, mobile_internet, duration))
            monthly_cost = tariff.select('ul/li/p/span[@class="monthlyPrice"]/text()').extract()[0].strip().replace(u'\xa3','')
            monthly_cost += tariff.select('ul/li/p/span[@class="monthlyPrice"]/span/text()').extract()[0].strip().replace(u'\xa3','')

            add_cart_url = tariff.select('ul/li/span/a[@name="Selectplan"]/@href').extract()[0]
            parsed = urlparse.urlparse(add_cart_url)
            params = urlparse.parse_qs(parsed.query)
            product_code = params['skuId'][0] + '-' + params['dependantSkuIds'][0]

            loader.add_value('identifier', product_code)
            loader.add_value('name', response.meta['device_name'] + ' - ' + tariff_name)
            loader.add_value('url', response.url)
            loader.add_value('brand', response.meta['site_name'].split()[0])
            price = tariff.select('ul/li[contains(@class, "phoneIncluded")]/p/text()').extract()[0].strip()
            loader.add_value('price', price)
            loader.add_value('image_url', response.meta.get('image_url'))

            product = loader.load_item()
            metadata = TelecomsMeta()
            metadata['device_name'] = response.meta['device_name']
            metadata['monthly_cost'] = monthly_cost
            metadata['tariff_name'] = tariff_name
            metadata['contract_duration'] = duration.split(' ')[0]
            metadata['operator'] = operator
            metadata['channel'] = channel
            if '4greadyplans' in tariff.select('@class').extract()[0]:
                net_gen = '4G'
            else:
                net_gen = '3G'
            metadata['network_generation'] = net_gen
            product['metadata'] = metadata

            yield product
