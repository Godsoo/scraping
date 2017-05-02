"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3977-express-gifts---spider-copy---very/details
"""
import paramiko
import csv
import os
import re
from tempfile import NamedTemporaryFile
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin
from scrapy.utils.response import get_base_url
from scrapy.utils.url import url_query_cleaner

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))

class VeryCoUk(BaseSpider):
    name = "expressgifts-very.co.uk"
    allowed_domains = ["very.co.uk"]
    start_urls = ["http://www.very.co.uk"]
    
    def parse(self, response):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "jqh3aMrK"
        username = "expressgifts"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        f = NamedTemporaryFile(delete=True, suffix='.csv', prefix='expressgifts_very_')
        sftp.get('express_gifts_flat_file.csv', f.name)

        with open(f.name) as csv_f:
            reader = csv.DictReader(csv_f)
            for row in reader:
                self.log(row)
                url = row['VERY'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

        f.close()

    def parse_product(self, response):
        
        
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('category', '//li[@typeof="v:Breadcrumb"]/a[@href!="/"]/text()')
        brand = hxs.select('//script[@type="text/javascript"]/text()').re('brand: *\"(.+)\"')
        loader.add_value('brand', brand)
        loader.add_xpath('image_url', '//div[@id="amp-originalImage"]/img/@src')
        loader.add_value('url', url_query_cleaner(response.url))
        loader.add_xpath('name', '//input[@name="speedtrapProductDisplayName"]/@value')
        item = loader.load_item()
        if hxs.select('//ul[@class="productOptionsList"]/li[contains(@class, "skuAttribute")]'):
            data = hxs.select('//script[contains(text(),"stockMatrix =")]/text()')[0].extract()
            data = data.replace('\n', '').replace('null', '"null"')
            data = re.search('stockMatrix = (.*?);', data, re.DOTALL)
            data = json.loads(data.group(1)) if data else []
            for i, variant in enumerate(data):
                sku = [elem for elem in variant if elem.startswith('sku')][0]
                sku_idx = variant.index(sku)
                product = Product(item)
                product['name'] = item['name'] + ' - ' + ' '.join(variant[:sku_idx]).title()
                product['identifier'] = '{}-{}'.format(response.meta.get('row').get('PRODUCT_NUMBER'), i)
                product['sku'] = product['identifier']
                product['price'] = variant[sku_idx + 2]
                product['stock'] = 1 if 'Available#Delivery' in variant[sku_idx + 1] else 0
                yield product
            return
        loader.add_value('identifier', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_value('sku', response.meta.get('row').get('PRODUCT_NUMBER'))
        loader.add_xpath('price', '//input[@name="speedtrapPrice"]/@value')
        stock = 1 if hxs.select('//meta[@property="product:availability"]/@content[.="In Stock"]') else 0
        loader.add_value('stock', stock)
        yield loader.load_item()
