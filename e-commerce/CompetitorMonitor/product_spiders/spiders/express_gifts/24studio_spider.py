import re
import os
import csv
import json
import paramiko

import urllib
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc


from expressgiftsitems import ExpressGiftsMeta

from scrapy import log

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class TwentyFourstudioSpider(BaseSpider):
    name = 'expressgifts-24studio.co.uk'
    allowed_domains = ['24studio.co.uk']

    start_urls = ['http://www.24studio.co.uk']

    def parse(self, response):
        base_url = get_base_url(response)

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        file_path = HERE + '/express_gifts_flat_file.csv'
        sftp.get('express_gifts_flat_file.csv', file_path)


        with open(file_path) as f:
            reader = csv.DictReader(f)
            search_url = 'http://homeshopping.24studio.co.uk/search/%s'
            for row in reader:
                url = search_url % row['PRODUCT_NUMBER'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        search_results = re.findall("ProductDetailsUrl = '(.*)';", response.body)
        if search_results:
            for search_result in search_results:
                yield Request(urljoin_rfc(base_url, search_result), callback=self.parse_product, meta=response.meta)
            return

        row = response.meta['row']

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', row['PRODUCT_NUMBER'])
        loader.add_value('sku', row['PRODUCT_NUMBER'])
        loader.add_value('brand', '24studio')
        loader.add_value('category', row['RANGE_DESCRIPTION'].strip())
        loader.add_value('name', row['DESCRIPTION'].strip())
        price = hxs.select('//div[@class="productDetailsInner"]//span[@class="now-price"]/text()').extract()[0]
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//meta[@property="og:image"]/@content')

        item = loader.load_item()

        metadata = ExpressGiftsMeta()
        metadata['buyer'] = row['BUYER'].strip()
        item['metadata'] = metadata

        product_options = re.findall('BasketProduct = (.*);', response.body)
        if product_options:
            for options in product_options:
                options = json.loads(options)['Members']
                for option in options:
                    for size_option in option['Sizes']:
                        if row['PRODUCT_NUMBER'] in ''.join(size_option['MemberValue'].split('-')):
                            option_item = deepcopy(item)
                            option_item['price'] = size_option['PriceIncludingDelivery']
                            if size_option['OutOfStock']:
                                option_item['stock'] = 0
                            item = option_item
                            break


        yield item
