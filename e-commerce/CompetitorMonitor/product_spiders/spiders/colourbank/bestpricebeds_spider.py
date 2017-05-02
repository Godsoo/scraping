import os
import re
import json
import csv
import itertools
import urlparse

from copy import deepcopy

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from scrapy import log

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class BestPriceBedsSpider(BaseSpider):
    name = 'bestpricebeds.co.uk'
    allowed_domains = ['bestpricebeds.co.uk']

    start_urls = ['http://www.bestpricebeds.co.uk/sitemap-brands.html']
    
    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:47.0) Gecko/20100101 Firefox/47.0'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for brand_url in hxs.select('//h2[@class="SiteMap"]/a/@href').extract():
            brand_url = add_or_replace_parameter(brand_url, 'page', '-1')
            yield Request(brand_url)

        for product_url in hxs.select('//ul[@class="SiteMap"]/li/a/@href').extract():
            yield Request(product_url)

        product_urls = hxs.select('//div[@class="producttext"]//a/@href').extract()
        for product_url in product_urls:
            yield Request(product_url)

        if re.search('pid(.*).html$', response.url):

            l = ProductLoader(item=Product(), response=response)
            l.add_xpath('name', '//*[@id="main"]//*[@itemprop="name"]/text()')
            l.add_value('url', response.url)
            l.add_value('sku', '')
            l.add_value('identifier', re.search('pid(.*).html', response.url).group(1))

            brand = hxs.select('//div[@class="brand-image"]/img/@alt').extract()
            if brand:
                l.add_value('brand', brand[0].replace(' at Best Price Beds', ''))
            else:
                l.add_value('brand', l.get_output_value('name').split()[0])
            image_url = hxs.select('//div[@class="large-img"]/a/img/@src').extract()
            image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
            l.add_value('image_url', image_url)
            category = hxs.select('//div[@id="breadcrumbs"]/ul/li/a/text()').extract()
            l.add_value('category', category[-1])
            price = response.xpath('//span[@class="sale-price"]/strong/text()').extract()

            if not price:
                price = response.xpath('//p[@class="price"]/strong/text()').extract()
            l.add_value('price', price[0])
            item = l.load_item()
            options = response.xpath('//select[@id="variant_id"]/option[@value!=""]')
            if options:
                for option in options:
                    option_value = option.select('@value').extract()[0]
                    option_name = option.select('text()').extract()[0]
                    yield Request(response.url + '?RC=100&var_id=' + option_value, callback=self.parse_options, meta={'item': item,
                                                                                                           'variant_id':option_value,
                                                                                                           'option_name': option_name})
            yield item

    def parse_options(self, response):
        try:
            hxs = HtmlXPathSelector(response)
            base_url = get_base_url(response)
            meta = response.meta

            url = response.meta['item']['url'] + '?RC=200'
            base_options = hxs.select('//select[contains(@name, "option_")]')
            options = []
            for base_option in base_options:
                select_id = base_option.select('@id').extract()[0]
                if base_option.select('@title').extract()[0] == 'Mattress Tension':
                    final_options = base_option.select('option[@value!=""]/@value').extract()
                else:
                    final_options = base_option.select(u'option[@value!="" and contains(text(), "(+")]/@value').extract()
                    final_options = final_options if final_options else base_option.select('option[@value!=""]/@value').extract()[0:1]
                options.append(map(lambda x: (select_id, x), final_options))
            options = list(itertools.product(*options))

            for option in options:
                formdata = {'ac': 'by', 'qty': '1', 'variant_id': meta.get('variant_id')}

                final_id = []
                final_name = []
                for option_id, value in option:
                    final_id.append(value)
                    final_name.append(hxs.select('//select[@id="' + option_id + '"]/option[@value="' + value + '"]/text()').extract()[0].split(' (')[0])
                    formdata[option_id] = value

                meta['final_identifier'] = meta.get('variant_id') + '-' + '-'.join(final_id)
                meta['final_name'] = meta.get('option_name') + ' ' + ' '.join(final_name)
                meta['dont_retry'] = True

                req = FormRequest(url=url, method='POST', formdata=formdata,
                                  callback=self.parse_option_price,
                                  meta=meta,
                                  dont_filter=True)
                yield req
        except:
            log.msg('Error while loading options')
            yield meta['item']

    def parse_option_price(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        meta = response.meta
        item = deepcopy(meta['item'])

        price = hxs.select('//span[@id="calcresult"]/text()').extract()
        price = extract_price(price[0]) if price else 0
        if price != item['price']:
            item['name'] += ' ' + meta['final_name']
            item['identifier'] = meta['final_identifier']
            item['price'] = price
            yield item
