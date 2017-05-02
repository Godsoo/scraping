import re
import os
import json
from urllib import urlencode
import hashlib
from decimal import Decimal
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse, TextResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.BeautifulSoup import BeautifulSoup
from pricecheck import valid_price

HERE = os.path.abspath(os.path.dirname(__file__))

class AmazonSpider(BaseSpider):
    name = 'axemusic-amazon.com'
    allowed_domains = [u'amazon.com', u'www.amazon.com']
    start_urls = (u'http://www.amazon.com', )

    def __init__(self, *args, **kwargs):
        super(AmazonSpider, self).__init__(*args, **kwargs)
        self.search_urls = (u'http://www.amazon.com/s/ref=nb_sb_noss?url=search-alias%%3Dmi&field-keywords=%(q)s',
                            u'http://www.amazon.com/s/ref=nb_sb_noss_2?url=search-alias%%3Dpopular&field-keywords=%(q)s',
                            u'http://www.amazon.com/s/ref=nb_sb_noss_1?url=search-alias%%3Dstripbooks&field-keywords=%(q)s')

    def start_requests(self):
        with open(os.path.join(HERE, 'amazon_skus.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['sku']
                url = self.search_urls[0]
                yield Request(url % {'q': sku}, meta={'name': row['name'], 'sku': sku, 'price': row['price'], 'search_urls': self.search_urls[1:]}, dont_filter=True)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        soup = BeautifulSoup(response.body)
        products = soup.find('div', id='atfResults')
        if products:
            products = products.findAll('div', id=re.compile('result_\d+$'))
            meta = response.meta
            meta['next_results'] = []
            # next_page = hxs.select(u'//a[@class="pagnNext"]/@href').extract()
            next_page = []
            if next_page:
                next_page = urljoin_rfc(get_base_url(response), next_page[0])
                meta['next_page'] = next_page
            for product in products:
                url = product.find('a')['href']
                url = urljoin_rfc(get_base_url(response), url)
                meta['next_results'].append(url)

            first_url = meta['next_results'][0]
            meta['next_results'] = meta['next_results'][1:]
            yield Request(first_url, callback=self.parse_product, meta=meta, dont_filter=True)
        else:
            log.msg('No products.')
            meta = response.meta
            if meta.get('search_urls'):
                search_url = meta['search_urls'][0]
                meta['search_urls'] = meta['search_urls'][1:]
                yield Request(search_url % {'q': meta['sku']}, meta=meta)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('name', u'//span[@id="btAsinTitle"]/text()')
        loader.add_value('url', response.url)

        loader.add_xpath('image_url', u'//tr[@id="prodImageContainer"]//img/@src')
        if not loader.get_output_value(u'image_url'):
            soup = BeautifulSoup(response.body)
            image_url = soup.find(lambda tag: tag.name == u'img' and tag.findParent(u'tr', id=u'prodImageContainer'))
            if image_url:
                loader.add_value('image_url', image_url.get(u'src'))

        loader.add_xpath('brand', u'//span[@class="tsLabel" and contains(text(),"Brand")]/following-sibling::span/text()')

        loader.add_xpath('price', u'//b[@class="priceLarge"]/text()')
        if not loader.get_output_value('price'):
            loader.add_xpath('price', u'//span[@class="priceLarge"]/text()')
        if not loader.get_output_value('price'):
            loader.add_xpath('price', u'//span[@class="price"]/text()')

        sku = hxs.select(u'//li/b[contains(text(),"Item model number")]/../text()').extract()
        if sku:
            sku = sku[0].strip()
        else:
            log.msg('No sku.')
        csv_sku = response.meta['sku'].strip()
        log.msg('SKU: [%s == %s]' % (sku.lower() if sku else u'None', csv_sku))

        csv_name = response.meta['name'].lower().split(u' ')
        site_name = loader.get_output_value('name').lower().split(u' ')
        log.msg(u'NAME: [%s == %s]' % (csv_name, site_name))
        name_match = any(map(lambda elem: elem in site_name, csv_name))

        if sku and (self.match_skus(sku, csv_sku) or self.match_skus(csv_sku, sku)) and name_match:
            if valid_price(response.meta['price'], loader.get_output_value('price')):
                loader.add_value('sku', response.meta['sku'])
                loader.add_value('identifier', response.meta['sku'].lower())
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
            elif meta.get('search_urls'):
                meta = response.meta
                search_url = meta['search_urls'][0]
                meta['search_urls'] = meta['search_urls'][1:]
                yield Request(search_url % {'q': meta['sku']}, meta=meta)

    def match_skus(self, sku1, sku2):
        sku1 = sku1.replace(u'-', u'').replace(u' ', u'').lower()
        sku2 = sku2.replace(u'-', u'').replace(u' ', u'').lower()
        return sku1 == sku2 or sku1.startswith(sku2) or sku1.endswith(sku2)
