import os
import csv
import gzip
import urllib
import cStringIO

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class AmazonTestSpider(BaseSpider):
    name = 'legotest-amazon.com'
    allowed_domains = ['iflamedataentry.com']
    start_urls = ('http://iflamedataentry.com/amazon/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
      
        gz_path = HERE+'/amazon.gz'

        file_url = hxs.select('//ul/li/a[text()!=" samples/"]/@href').extract()[-1]
        file_url = urljoin_rfc(base_url, file_url)
        urllib.urlretrieve (file_url, gz_path)

        
        with gzip.open(gz_path, 'rb') as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for row in reader:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', row['Identifier'].decode('utf8', 'ignore'))
                loader.add_value('name', row['Product_Name'].decode('utf8', 'ignore'))
                loader.add_value('url', row['URL'].decode('utf8', 'ignore'))
                loader.add_value('brand', row['Brand'].decode('utf8', 'ignore'))
                loader.add_value('price', row['Price'].decode('utf8', 'ignore'))
                if 'IN STOCK' not in row['Stock_Availability'].upper():
                        loader.add_value('stock', 0)
                loader.add_value('shipping_cost', row['Shipping_Price'].decode('utf8', 'ignore'))
                loader.add_value('image_url', row['Image_URL'].decode('utf8', 'ignore'))
                loader.add_value('sku', row['SKU'].decode('utf8', 'ignore'))
                loader.add_value('dealer', row['Dealer_Name'].decode('utf8', 'ignore'))
                yield loader.load_item()

