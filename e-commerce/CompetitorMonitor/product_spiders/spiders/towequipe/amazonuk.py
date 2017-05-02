import re
import os
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse, TextResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib
from decimal import Decimal

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.BeautifulSoup import BeautifulSoup
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class AmazonSpider(BaseSpider):
    name = 'towequipe-amazon.co.uk'
    allowed_domains = ['amazon.co.uk', 'www.amazon.co.uk']
    start_urls = (u'http://www.amazon.co.uk', )

    def __init__(self, *args, **kwargs):
        super(AmazonSpider, self).__init__(*args, **kwargs)
        self.search_url = u'http://www.amazon.co.uk/s/ref=sr_nr_p_6_1?rh=n%%3A248877031%%2Ck%%3Awitter+%(q)s%%2Cp_6%%3AA3TZG77SD6Z3FB&bbn=248877031&keywords=witter+%(q)s&ie=UTF8&qid=1354641669&rnid=301351031'

    def start_requests(self):
        with open(os.path.join(HERE, 'products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                partn = row['partn']
                sku = row['SKU']
                url = self.search_url
                yield Request(url % {'q': sku}, meta={'sku': sku, 'partn': partn}, dont_filter=True)


    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        products = hxs.select(u'//div[@id="atfResults"]//div[starts-with(@id,"result_")]')
        if products:
            meta = response.meta
            meta['next_results'] = []
            next_page = hxs.select(u'//a[@class="pagnNext"]/@href').extract()
            if next_page:
                next_page = urljoin_rfc(get_base_url(response), next_page[0])
                meta['next_page'] = next_page
            for product in products:
                url = product.select(u'.//a[@class="title"]/@href')
                if not url:
                    url = product.select(u'.//h3[@class="newaps"]/a/@href')
                if url:
                    url = url[0].extract()
                else:
                    continue
                url = urljoin_rfc(get_base_url(response), url)
                soup = BeautifulSoup(product.extract())
                price = soup.find('ul', attrs={'class': 'rsltL'})
                if price:
                    price = price.findAll('span')[0]
                if not price:
                    price = soup.find('span', 'price addon')
                if not price:
                    price = soup.find('span', 'price')
                if price:
                    price = price.string.strip()[1:]
                if not price:
                    price = '1000.00'
                meta['next_results'].append({'price': float(price), 'url': url})

            meta['next_results'].sort(key=lambda elem: elem.get('price'))
            meta['next_results'] = [elem['url'] for elem in meta['next_results']]
            first_url = meta['next_results'][0]
            meta['next_results'] = meta['next_results'][1:]
            yield Request(first_url, callback=self.parse_product, meta=meta, dont_filter=True)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('name', u'//span[@id="btAsinTitle"]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('price', u'//b[@class="priceLarge"]/text()')
        loader.add_xpath('image_url', u'//tr[@id="prodImageContainer"]//img/@src')
        if not loader.get_output_value(u'image_url'):
            soup = BeautifulSoup(response.body)
            image_url = soup.find(lambda tag: tag.name == u'img' and tag.findParent(u'tr', id=u'prodImageContainer'))
            if image_url:
                loader.add_value('image_url', image_url.get(u'src'))

        loader.add_xpath('brand', u'//span[@class="tsLabel" and contains(text(),"Brand")]/following-sibling::span/text()')
        if not loader.get_output_value('price'):
            loader.add_xpath('price', u'//span[@class="priceLarge"]/text()')
        if not loader.get_output_value('price'):
            loader.add_xpath('price', u'//span[@class="price"]/text()')
        partn = hxs.select(u'//span[@class="tsLabel" and contains(text(),"Manufacturer Part Number")]/following-sibling::span/text()').extract()
        if not partn:
            partn = hxs.select(u'//tr/td[contains(text(),"Manufacturer Part Number")]/following-sibling::td/text()').extract()
        partn = partn[0].strip()
        log.msg('PARTN: [%s == %s]' % (partn.lower(), response.meta['partn'].lower()))
        log.msg('SKU: [%s == %s]' % (partn.lower(), response.meta['sku'].lower()))
        sold_by = hxs.select(u'//div[contains(text(),"Sold by")]/b/text()').extract()
        sold_by = sold_by[0].strip() if sold_by else u''
        log.msg(u'Sold by: %s' % sold_by)
        if (partn.lower() == response.meta['partn'].lower() or partn.lower() == response.meta['sku'].lower()) and sold_by != u'Towequipe':
            loader.add_value('sku', response.meta['partn'])
            loader.add_value('identifier', response.meta['partn'].lower())
            # if loader.get_output_value('price'):
            yield loader.load_item()
        else:
            meta = response.meta
            next_result = meta['next_results']
            if next_result:
                next_result = next_result[0]
                meta['next_results'] = meta['next_results'][1:]
                yield Request(next_result, callback=self.parse_product, meta=response.meta)
            elif meta.get('next_page'):
                next_page = meta['next_page']
                yield Request(next_page, meta=response.meta)