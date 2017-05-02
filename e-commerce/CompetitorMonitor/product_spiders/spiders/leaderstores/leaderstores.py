# -*- coding: utf-8 -*-
"""
Customer: Leader Stores
Website: http://www.leaderstores.co.uk
Extract the items from the feed that are in the SFTP file
"""

import csv
import os
import paramiko
from decimal import Decimal
from scrapy.spiders import XMLFeedSpider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from product_spiders.utils import extract_price


HERE = os.path.abspath(os.path.dirname(__file__))


class LeaderStoresSpider(XMLFeedSpider):
    name = 'leaderstores-leaderstores.co.uk'
    allowed_domains = ['leaderstores.co.uk']
    start_urls = ('https://www.leaderstores.co.uk/googleproducts/getXML',)
    itertag = 'item'

    sftp_username = "leaderstores"
    sftp_password = "AgaeX3LE"
    local_filename = os.path.join(HERE, 'leaderstores_skus.csv')
    remote_filename = 'Product Information.csv'
    remote_costprices = 'costprices.csv'
    local_costprices = os.path.join(HERE, 'leaderstores_costprices.csv')

    def __init__(self, *args, **kwargs):
        super(LeaderStoresSpider, self).__init__(*args, **kwargs)


    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))

        transport.connect(username=self.sftp_username, password=self.sftp_password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        sftp.get(self.remote_filename, self.local_filename)
        sftp.get(self.remote_costprices, self.local_costprices)

        transport.close()

        self.id_code_map = {}
        with open(self.local_filename) as f:
            reader = csv.reader(f)
            reader.next()
            for row in reader:
                self.id_code_map[row[0].lower().replace('sku-', '')] = row[1].lower()

        self.cost_prices = {}
        with open(self.local_costprices) as f:
            reader = csv.reader(f)
            reader.next()
            for row in reader:
                self.cost_prices[row[0].lower()] = row[7]

        return super(LeaderStoresSpider, self).parse(response)

    def parse_node(self, response, node):
        identifier = node.select('./*[local-name()="id"]/text()')[0].extract()
        if identifier not in self.id_code_map:
            return
        product_code = self.id_code_map[identifier]
        loader = ProductLoader(item=Product(), selector=node)
        size = node.xpath('./*[local-name()="size"]/text()').extract()
        color = node.xpath('./*[local-name()="color"]/text()').extract()
        material = node.xpath('./*[local-name()="material"]/text()').extract()
        name = node.xpath('./*[local-name()="parent_title"]/text()').extract()
        if not name:
            name = node.xpath('./title/text()').extract()
        name = name[0]
        if material:
            name += u' {}'.format(material[0])
        if color:
            name += u' {}'.format(color[0])
        if size:
            name += u' {}'.format(size[0])
        price = node.xpath('./*[local-name()="price"]/text()').extract_first()
        pack_size = node.xpath('./description/text()').re('Pack Size m: *([\d.]+)')
        if pack_size:
            price = extract_price(price) * extract_price(pack_size[0])
            
        loader.add_value('name', name)
        loader.add_xpath('url', './link/text()')
        loader.add_xpath('image_url', './*[local-name()="image_link"]/text()')
        loader.add_value('identifier', identifier)
        loader.add_value('price', price)
        loader.add_xpath('shipping_cost', './*[local-name()="shipping"]/*[local-name()="price"]/text()')
        loader.add_xpath('brand', './*[local-name()="brand"]/text()')
        loader.add_xpath('category', './*[local-name()="google_product_category"]/text()')
        loader.add_xpath('sku', './*[local-name()="mpn"]/text()')
        stock = node.xpath('./*[local-name()="availability"]/text()').extract()
        if stock and stock[0] == 'out of stock':
            loader.add_value('stock', 0)

        item = loader.load_item()

        if product_code in self.cost_prices:
            try:
                cost_price = Decimal(self.cost_prices[product_code])
            except:
                self.log('ERROR: unable to set cost price for item %r' % item)
            else:
                item['metadata'] = {'cost_price': str(cost_price)}
        
        if pack_size:
            yield Request(loader.get_output_value('url'), 
                          self.parse_pack_price,
                          meta={'item': item})
        else:
            yield item
        
    def parse_pack_price(self, response):
        item = response.meta['item']
        item['price'] = response.xpath('//span[@itemprop="price"]/@content').extract_first()
        yield item
        
