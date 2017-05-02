import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
import paramiko
from product_spiders.items import Product, ProductLoader
from scrapy.http import Request

from fmgitems import FMGMeta

from urlparse import urljoin

HERE = os.path.abspath(os.path.dirname(__file__))


class MailspeedMarineFeedSpider(BaseSpider):
    name = 'fmg_mailspeedmarine-feed'
    allowed_domains = ['mailspeedmarine.com']
    start_urls = ('http://mailspeedmarine.com',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        host = "144.76.118.46"
        port = 22
        transport = paramiko.Transport((host, port))
        username = 'equinesuperstore'
        password = 'vikBeOmy'
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        skus_filepath = '/upload/equinesuperstore/MSM_Products_for_Pricing_Tool.csv'
        products_filepath = '/upload/equinesuperstore/MSM_Export_Price_Comparison.csv'
        products_localpath = '/tmp/mailspeedmarine_products.csv'
        sftp.get(products_filepath, products_localpath)
        sftp.close()
        transport.close()


        with open(products_localpath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = urljoin(self.start_urls[0], row['Product URL'].decode('utf8', 'ignore'))
                loader = ProductLoader(item=Product(), selector=hxs)
                try:
                    loader.add_value('sku', row['SKU'])
                    loader.add_value('identifier', row['SKU'])
                except Exception:
                    loader.add_value('sku', row['SKU'].decode('iso-8859-15'))
                    loader.add_value('identifier', row['SKU'].decode('iso-8859-15'))

                loader.add_value('brand', row['Brand'])
                if row['In_Stock'] == "no":
                    loader.add_value('stock', 0)
                loader.add_value('url', url)
                loader.add_value('name', row['Product_Name'].decode('iso-8859-15'))
                loader.add_value('price', row['Product_Price'] or '0')
                loader.add_value('category', row['Categories'].decode('iso-8859-15'))
                discontinued = False
                if 'Discontinued' in row:
                    discontinued = str(row['Discontinued']).strip() == '1'
                product = loader.load_item()

                metadata = FMGMeta()
                metadata['discontinued'] = discontinued
                metadata['colour'] = row['Colour']
                metadata['size'] = row['Size']
                metadata['variant'] = row['Variant']
                metadata['feature'] = row['Feature']
                product['metadata'] = metadata

                yield Request(url, callback=self.parse_to_get_img, meta={'product': product})

    def parse_to_get_img(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta.get('product', Product())
        image_url = hxs.select('//div[@class="product-img-box"]//a/img/@src').extract()
        if image_url:
            product['image_url'] = image_url[0]

        yield product
