from decimal import Decimal, ROUND_DOWN, ROUND_UP
import re
import json
import os
import csv
import xlrd
import paramiko

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.item import Item, Field
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO
from product_spiders.spiders.bi_worldwide_usa.biworldwideitem import BIWordlwideMeta

from product_spiders.utils import extract_price
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

class USNFeedMeta(Item):
    ASIN = Field()

def format_price(price, rounding=None):
    if price is None:
        return Decimal('0.00')

    return price.quantize(Decimal('0.01'), rounding=rounding or ROUND_UP)

HERE = os.path.abspath(os.path.dirname(__file__))

class USNBaseSpider(BaseSpider):
    name = 'uk.usn-sport.com'
    start_urls = ('http://uk.usn-sport.com',)
    allowed_domains = ['uk.usn-sport.com']
    file_start_with = 'usn_client_file'
    handle_httpstatus_list = [404]
    xls_file_path = 'usn_feed.xlsx'
    csv_file_path = 'usn_feed.csv'

    identifiers = []

    def __init__(self, *args, **kwargs):
        super(USNBaseSpider, self).__init__(*args, **kwargs)
        images_csv = os.path.join(HERE, 'usn_images.csv')
        self.images = dict()
        with open(images_csv) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.images[row['identifier']] = row['image_url']

    def parse(self, response):

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "dy6ZqECj"
        username = "ultimatesportsnutrition"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last = get_last_file(self.file_start_with, files)

        sftp.get(last.filename, self.csv_file_path)

        # Convert XLXS file to CSV
        #excel_to_csv(self.xls_file_path, self.csv_file_path)

        with open(self.csv_file_path) as f:
            reader = UnicodeDictReader(f) # csv.DictReader(f, delimiter=',')
            for row in reader:
                if row['Item Code'].lower() in self.identifiers:
                    continue

                self.identifiers.append(row['Item Code'].lower())
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', row['Item Code'])
                loader.add_value('sku', row['Item Code'])
                loader.add_value('name', row['Product Description'])
                loader.add_value('price', row['RRP'])
                loader.add_value('brand', 'USN')
                loader.add_value('category', row['Category'])
                image_url = self.images.get(row['Item Code'])
                if image_url:
                    loader.add_value('image_url', image_url)
                loader.add_value('url', row['USN Url:'])
                product = loader.load_item()
                metadata = USNFeedMeta()
                metadata['ASIN'] =  row['ASIN'] if row['ASIN'].lower() != 'n/a' else ''
                product['metadata'] = metadata
                yield Request(product['url'], callback=self.parse_details, meta={'product': product, 'option_id': row['Option Value']}, dont_filter=True)

    def parse_details(self, response):
        if response.status == 404:
            yield response.meta.get('product')
            return
        hxs = HtmlXPathSelector(response)
        product = response.meta.get('product')
        image_url = hxs.select('//div[@class="MagicScroll"]//img/@src').extract()
        if image_url:
            product['image_url'] = image_url[0]
        option_id = response.meta.get('option_id')

        product_info = re.search('Product\.Config\((.*)\);', response.body)
        if not product_info or option_id.lower().strip() == 'n/a':
            product_info = json.loads(re.search('Product\.OptionsPrice\((\{.*)\);', response.body).group(1))
            product['price'] = format_price(Decimal(product_info['productPrice']))
            yield product
            return

        product_info = json.loads(product_info.group(1))
        stock = json.loads(re.search('StockStatus\((.*)\);', response.body).group(1))

        base_price = Decimal(product_info['basePrice'])
        options = sum([option['options'] for option in product_info['attributes'].values()], [])
        for option in options:
            if option['id'] == option_id:
                product['price'] = format_price(base_price + Decimal(option['price']))
                if stock.get('option_id') and not stock[option_id]['is_in_stock']:
                    product['stock'] = 0


                yield product

def get_last_file(start_with, files):
    """
    Returns the most recent file, for the file name which starts with start_with

    :param start_with: the file name has this form start_with + date
    :param files: files list sftp.listdir_attr
    """
    last = None
    for f in files:
        if ((last == None and start_with in f.filename and 
             f.filename.endswith('.csv')) or 
            (start_with in f.filename and f.filename.endswith('.csv') and 
             f.st_mtime > last.st_mtime)):
            last = f
    return last


def excel_to_csv(xls_filename, csv_filename):
    wb = xlrd.open_workbook(xls_filename)
    sh = wb.sheet_by_index(0)
    csv_file = open(csv_filename, 'wb')
    wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

    for rownum in xrange(sh.nrows):
        row = sh.row(rownum)
        wr.writerow([unicode(col.value).encode('utf8') for col in sh.row(rownum)])

    csv_file.close()

def UnicodeDictReader(utf8_data):
    csv_reader = csv.DictReader(utf8_data)
    for row in csv_reader:
        yield {key: unicode(value, 'utf-8') for key, value in row.iteritems()}