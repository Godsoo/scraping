# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from scrapy.utils.url import add_or_replace_parameter
import re
import json
import os
import csv

from scrapy import log


HERE = os.path.abspath(os.path.dirname(__file__))


class CyberportSpider(BaseSpider):
    name = u'cyberport.de'
    allowed_domains = ['www.cyberport.de']
    start_urls = ('http://www.cyberport.de/logitech',)

    map_products_csv = os.path.join(HERE, 'logitech_map_products.csv')
    map_price_field = 'map'
    map_join_on = [('sku', 'mpn'), ('sku', 'ean13')]

    def start_requests(self):

        for url in self.start_urls:
            yield Request(url)

        with open(HERE + '/logitech_extra_products.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Cyberport'] != 'No Match':
                    yield Request(row['Cyberport'], callback=self.parse_product, meta={'sku':row['sku'], 'brand':row['brand']})

    def _get_form_request(self, hxs, page):
        ajax_url = hxs.select('//form[@class="filter"]/@action').extract()
        ajax_url = urljoin_rfc('http://www.cyberport.de/', ajax_url[0])
        headers = {
            'X-Prototype-Version': '1.7',
            'X-Requested-With': 'XMLHttpRequest',
        }
        form_search = hxs.select('//form[@id="dyn-formid-01"]')
        ajax_url =  urljoin_rfc('http://www.cyberport.de/', form_search.select('@action').extract()[0])
        formdata = dict(zip(form_search.select('fieldset/input/@name').extract(), form_search.select('fieldset/input/@value').extract()))
        filter_data = json.loads(formdata['filterJSON'])
        filter_data[u'SID_ITEMSPERPAGE'] = '40'
        filter_data[u'itemsPerPage'] = '40'
        filter_data[u'page'] = str(page)
        formdata.update(filter_data)
        formdata['filterJSON'] = json.dumps(filter_data)
        return FormRequest(
            ajax_url,
            formdata=formdata,
            headers=headers,
            callback=self.parse_list,
            dont_filter=True,
            meta={'page': page})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        yield self._get_form_request(hxs, page=1)

    def parse_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="itemLine posRel0"]/@id').extract()
        for product_id in products:
            url = 'http://www.cyberport.de/?EVENT=item'
            url = add_or_replace_parameter(url, 'ARTICLEID', product_id.replace('itemLine', ''))
            yield Request(url, callback=self.parse_product)
        if len(products) == 40:
            page = response.meta.get('page', 1)
            page += 1
            yield self._get_form_request(hxs, page)

    def parse_item(self, response):
        for match in re.finditer(r'<a class=\\"hint\\" title=\\"Weitere Informationen zum Produkt\\" href=\\"\\/(.*?)\\"', response.body):
            url = match.group(1)
            yield Request(urljoin_rfc('http://www.cyberport.de/', url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()
        loader.add_value('name', name)
        identifier = hxs.select('//div[@id="article_cont"]//div[@class="itemcostinfo"]/@itemid').extract()[0]
        loader.add_value('identifier', identifier)

        sku = response.meta.get('sku', '')
        if sku:
            loader.add_value('sku', sku)
            loader.add_value('brand', response.meta.get('brand', ''))
        else:
            sku = hxs.select('//span[@id="hbNrDataSheet"]/text()').extract()
            if sku:
                loader.add_value('sku', sku[0])
            loader.add_value('brand', 'Logitech')

        loader.add_value('url', response.url)
        image_url = hxs.select('//ul[@id="gliderSmall"]/li/a/@onclick').extract()
        if image_url:
            match = re.search(r"imgSrc: '(.*?)',", image_url[0])
            if match:
                image_url = match.group(1)
                loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        else:
            image_url = hxs.select('//img[@id="itemDetail{}"]/@src'.format(identifier)).extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//meta[@itemprop="price"]/@content').extract()
        price = extract_price(price[0])
        loader.add_value('price', price)
        in_stock = hxs.select('//meta[@itemprop="availability"]/@content').extract()[0].strip()
        if in_stock == 'out_of_stock':
            loader.add_value('stock', 0)
        category = hxs.select('//*[@id="main-centercontainer"]/div[1]/a[3]/text()').extract()
        if category:
            loader.add_value('category', category[0])
        shipping = '0.0'
        shipping_base = hxs.select('//div[@class="clear fl b8"]/span[@class="basis fl"]/text()').extract()
        if shipping_base:
            shipping = shipping_base[0].replace(',', '')
            shipping_decimal = hxs.select('//div[@class="clear fl b8"]/span[@class="decimal fl"]/text()').extract()
            if shipping_decimal:
                shipping += '.' + shipping_decimal[0]
        loader.add_value('shipping_cost', extract_price(shipping))
        yield loader.load_item()
