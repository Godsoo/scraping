import os
import re
import csv
import paramiko

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class ExpressGiftsArgosSpider(BaseSpider):
    name = 'expressgifts-argos'
    allowed_domains = ['argos.co.uk', 'argos.scene7.com']
    start_urls = ['http://argos.co.uk']

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
                url = row['ARGOS'].strip()
                if url:
                    yield Request(url, dont_filter=True, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        row = response.meta['row']

        url = response.url
        l = ProductLoader(item=Product(), response=response)

        # name
        name = hxs.select("//div[@id='pdpProduct']/h1/text()").extract()
        if not name:
            name = hxs.select('//h2[@class="product-title"]/text()').extract()

        if not name:
            self.log("ERROR! NO NAME! %s" % url)
            log.msg('ERROR! NO NAME!')
            if response.url.endswith('.htm'):
                yield Request(response.url.replace('.htm', '.html'), callback=self.parse_product, meta=response.meta)
            return
        name = name[0].strip()
        l.add_value('name', name)

        # price
        price = hxs.select("//span[contains(@class, 'actualprice')]/span/text()").extract()
        if not price:
            price = hxs.select('//ul/li[@class="price"]/text()').extract()
        price = extract_price("".join(price))
        l.add_value('price', price)

        # sku
        sku = row['PRODUCT_NUMBER']
        l.add_value('sku', sku)
        l.add_value('identifier', sku)

        # category

        categories = re.findall('br_data.cat = "(.*)";', response.body)
        if not categories:
            categories = hxs.select("//div[@id='breadcrumb']//li[position() = (last() -1) or position() = (last() -2) or position() = (last() - 3)]//text()").extract()

        if categories:
            categories = categories[0].split('|')[-1]
        else:
            categories = ''

        l.add_value('category', categories)

        # product image
        l.add_xpath('image_url', "//div[@id='pdpMedia']//div[@id='main']/img[1]/@src")
        # url
        l.add_value('url', url)
        # brand
        l.add_xpath('brand', "//strong[@class='pdp-view-brand-main']/text()")

        
        if not l.get_output_value('price'):
            l.add_value('stock', 0)

        product = l.load_item()

        meta_data = ' '.join([x.strip() for x in hxs.select("//span[@class='wasprice']//text()").extract()])
        product['metadata'] = {}
        product['metadata']['promotional_data'] = meta_data

        if not product.get('image_url', None):
            image_url_req = 'http://argos.scene7.com/is/image/Argos?req=set,json&imageSet='+product['identifier']+'_R_SET'
            yield Request(image_url_req, callback=self.parse_image, meta={'product': product})
        else:
            yield product

    def parse_image(self, response):
        product = response.meta['product']
        image_url = re.findall('"img_set","n":"(.*)","item', response.body)
        if image_url:
            image_url = 'http://argos.scene7.com/is/image/' + image_url[0]
            product['image_url'] = image_url

        yield product
