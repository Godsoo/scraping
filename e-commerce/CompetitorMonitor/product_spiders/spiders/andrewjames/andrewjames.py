"""
Andrew James client spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4717
"""

import re
import csv
import os
import json
import itertools
import paramiko
from urllib2 import urlopen
from w3lib.url import add_or_replace_parameter, url_query_cleaner

from scrapy.spiders import SitemapSpider
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from andrewjamesitems import AndrewJamesMeta

HERE = os.path.abspath(os.path.dirname(__file__))

def get_last_file(files):
    exts = ('.csv')
    last = None
    for f in files:
        if ((last == None and f.filename[-4:] in exts) or 
            (f.filename[-4:] in exts and 
             f.st_mtime > last.st_mtime)):
            last = f
    return last


class AndrewJames(SitemapSpider):
    name = "andrewjames-andrewjames"
    allowed_domains = ("andrewjamesworldwide.com",)
    sitemap_urls = ['https://www.andrewjamesworldwide.com/robots.txt']
    sitemap_rules = [('p\d+$', 'parse_product')]
    
    def __init__(self, *args, **kwargs):
        super(AndrewJames, self).__init__(*args, **kwargs)
        self.skus = {}
        self.skus_found = set()
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "5H3xcABq"
        username = "andrewjames"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()
        
        file_path = HERE + '/products.csv'
        sftp.get(get_last_file(files).filename, file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['SKU'].strip()
                if sku.startswith('AJ'):
                    self.skus[sku] = row
        self.log("%d SKU's are found in the feed file" %len(self.skus.keys()))
        
    def parse_product(self, response):
        base_sku = response.xpath('//@data-ref').extract_first()
        identifier = re.search('p(\d+)$', url_query_cleaner(response.url)).group(1)
        url = 'https://www.andrewjamesworldwide.com/ajax/get_product_options/{0}'.format(identifier)
        data = json.load(urlopen(url))
        attributes = [attr['values'] for attr in data['attributes']]
        if [] in attributes:
            url = add_or_replace_parameter(url, 
                                           'attributes[1]', 
                                           attributes[0][0]['value_id'])
            data = json.load(urlopen(url))
            attributes = [attr['values'] for attr in data['attributes']]
        variants = itertools.product(*attributes)
        for variant in variants:
            url = 'https://www.andrewjamesworldwide.com/ajax/get_product_options/{0}'.format(identifier)
            for idx, option in enumerate(variant):
                url = add_or_replace_parameter(url, 'attributes[{0}]'.format(idx+1), option['value_id'])
            data = json.load(urlopen(url))
            selection = data['selection'].values()[0]
            sku = selection['reference'].strip()
            if not sku and base_sku not in self.skus_found:
                sku = base_sku
            if sku not in self.skus.keys():
                continue
            if sku in self.skus_found:
                self.logger.info('Duplicated SKU is found: %s' %sku)
            self.skus_found.add(sku)
            
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('sku', sku)
            loader.add_value('identifier', selection['product_id'])
            loader.add_xpath('name', '//span[@id="js-product-title"]/text()')
            loader.add_value('name', [option['value'] for option in variant])
            loader.replace_value('name', selection['title'])
            loader.add_value('url', response.url)
            loader.add_value('price', selection['price_inc'])
            category = response.css('div.breadcrumb a::attr(title)').extract()
            loader.add_value('category', category[1:])
            try:
                image_url = [attr['images'][0]['image'] for attr in data['attributes'][-1]['values']]
            except IndexError:
                image_url = response.xpath('//div[@id="js-product-image"]//@src').extract()
            loader.add_value('image_url', response.urljoin(image_url[0]))
            loader.add_value('brand', "Andrew James")
            item = loader.load_item()
            
            metadata = AndrewJamesMeta()
            metadata['asin'] = self.skus[sku]['ASIN']
            item['metadata'] = metadata
            yield item
        
    def closed(self, reason):
        skus = set(self.skus.keys()) - self.skus_found
        if not skus:
            return
        self.logger.info("%d SKU's haven't been found:" %len(skus))
        self.logger.info(', '.join(str(sku) for sku in skus))
        for sku in skus:
            self.logger.info(sku)
