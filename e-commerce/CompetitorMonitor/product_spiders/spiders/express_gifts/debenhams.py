import os
import paramiko
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
import csv
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from scrapy import log

from urlparse import urljoin

import json
import copy

from scrapy.item import Item, Field

HERE = os.path.abspath(os.path.dirname(__file__))


class YMeta(Item):
    promotions = Field()


class ExpressGiftsDebenhamsSpider(BaseSpider):
    name = 'expressgifts-debenhams'
    start_urls = ['http://www.debenhams.com/']
    id_seen = []

    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        file_path = HERE + '/express_gifts_flat_file.csv'
        sftp.get('express_gifts_flat_file.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row['DEBENHAMS'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        row = response.meta['row']

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//div[@id="product-item-no"]/p/text()').extract()
        if not tmp:
            tmp = hxs.select('//meta[@property="product_number"]/@content').extract()
        if tmp:
            loader.add_value('identifier', tmp[0].replace('Item No.',''))
            loader.add_value('sku', row['PRODUCT_NUMBER'])
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        name = ''
        tmp = hxs.select('//h1[@class="catalog_link"]/span[@itemprop="name"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        stock = 0
        tmp = hxs.select('//div[@itemprop="offers"]/span[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip().replace(',',''))
            loader.add_value('price', price)
            stock = 1
        #stock
        #tmp = hxs.select('//form[@id="save-product-to-cart"]//p[not(contains(@class,"hidden"))]/strong[text()="Out of stock"]')
        #if tmp:
        #    stock = 0
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//div[@id="image_viewer"]//img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        #brand
        tmp = hxs.select('//h1[@class="catalog_link"]/span[@itemprop="brand"]/text()').extract()
        if tmp:
            loader.add_value('brand', tmp[0].strip())
        #category
        tmp = hxs.select('//div[@class="breadcrumb_links" and not(@id)]//a/text()').extract()
        if len(tmp)>3:
            tmp = tmp[-3:]
        if tmp:
            for s in tmp:
                loader.add_value('category', s.strip())
        #shipping_cost
        if price<30:
            loader.add_value('shipping_cost', 3.49)

        product = loader.load_item()

        metadata = YMeta()
        tmp = hxs.select('//p[@class="price-off-and-save"]//text()').extract()
        if tmp:
            metadata['promotions'] = ' '.join([s.strip() for s in tmp if s.strip()])
        product['metadata'] = metadata

        options = None
        tmp = hxs.select('//div[contains(@id,"entitledItem_")]/text()').extract()
        if tmp:
            j = json.loads(tmp[0].replace("'",'"'))
            if j:
                options = j
        #process options
        if options:
            for opt in options: ###
                item = copy.deepcopy(product)
                tmp = opt.get('catentry_id', None)
                if tmp:
                    item['identifier'] += '-' + tmp
                tmp = opt.get('Attributes', None)
                if tmp:
                    item['name'] = name + ' - ' + '-'.join([s for s in tmp.keys()])
                tmp = opt.get('offer_price', None)
                if tmp:
                    price = extract_price(tmp.replace('Now','').strip().replace(',',''))
                    item['price'] = price
                    item['stock'] = 1
                tmp = opt.get('inventory_status', None)
                if tmp and tmp=='Unavailable':
                    item['stock'] = 0

                if not item.get('identifier', None):
                    log.msg('### No product ID at '+response.url, level=log.INFO)
                else:
                    if not item['identifier'] in self.id_seen:
                        self.id_seen.append(item['identifier'])
                        yield item
                    else:
                        log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
            return

        #no options
        if not product.get('identifier', None):
            log.msg('### No product ID at '+response.url, level=log.INFO)
        else:
            if not product['identifier'] in self.id_seen:
                self.id_seen.append(product['identifier'])
                yield product
            else:
                log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
