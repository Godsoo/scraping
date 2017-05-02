import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
import paramiko
from product_spiders.items import Product, ProductLoader

from scrapy.item import Field, Item

HERE = os.path.abspath(os.path.dirname(__file__))


class Meta(Item):
    cost_price = Field()


class AttractionTixSpider(BaseSpider):
    name = 'attractiontix.co.uk'
    allowed_domains = ['attractiontix.co.uk']
    start_urls = ('http://www.attractiontix.co.uk/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        host = "144.76.118.46"
        port = 22
        transport = paramiko.Transport((host, port))
        username = 'attractiontix'
        password = 'I8nKpd4'
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        filepath = '/upload/attractiontix/ATixProductMargins.csv'
        localpath = os.path.join(HERE, 'atix.csv')
        sftp.get(filepath, localpath)
        sftp.close()
        transport.close()

        with open(os.path.join(HERE, 'atix.csv')) as f:
            reader = csv.DictReader(f)
            for raw_row in reader:
                row = {}
                for key, value in raw_row.iteritems():
                    if key:
                        row[key.decode('utf8').encode('ascii', 'ignore').strip()] = value

                d = row['DateFrom'].split('/')
                if len(d[-1]) < 4:
                    d[-1] = '20' + d[-1]
                row['DateFrom'] = '/'.join(d)
                loader = ProductLoader(item=Product(), selector=hxs)
                brand = row['PriceType']
                if brand not in ['Adult', 'Child']:
                    brand = 'Adult'
                loader.add_value('sku', row['DateFrom'])
                loader.add_value('brand', brand)
                loader.add_value('name', row['TicketName'].decode('iso-8859-15'))
                loader.add_value('price', row['SellPriceGBP'] or '0')
                loader.add_value('category', row['Region'].decode('iso-8859-15'))
                loader.add_value('url', row['ProductURL'].decode('utf8', 'ignore'))
                loader.add_value('identifier', row['ServiceID'] + ':' + row['DateFrom'] + ':' + row['PriceType'])

                meta_ = Meta()
                meta_['cost_price'] = row['BuyPriceGBP']
                p = loader.load_item()
                p['metadata'] = meta_

                yield p
