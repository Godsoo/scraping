import os
import csv
import cStringIO
import paramiko

# NETFS105, FS105UK -> FS105
def fix_sku(a, b):
    return None  # Don't remove region codes
    a = a.lower()
    for i in xrange(1, 3):
        if a.endswith(b[:-i].lower()):
            return b[:-i]

HERE = os.path.abspath(os.path.dirname(__file__))
def get_whitelist(rows):
    if not rows:
        return None, None

    temp_row = rows[0]

    manuf_sku_field = None
    comms_sku_field = None
    desc_field = None

    for field in temp_row:
        if 'Manufac pt n.o'.lower() in field.lower():
            manuf_sku_field = field
        elif 'Our Pt.n.o'.lower() in field.lower():
            comms_sku_field = field
        elif 'Description'.lower() in field.lower():
            desc_field = field

    whitelist = set()
    product_list = {}
    for row in rows:
        sku1 = row[manuf_sku_field].strip()
        sku2 = row[comms_sku_field].strip()

        # Remove region code from D-Link products
        if sku1.endswith('/B'): sku1 = sku1[:-2]
        if sku2.endswith('/B'): sku2 = sku2[:-2]

        whitelist.add(sku1 or sku2)
        product_list[sku1 or sku2] = row[desc_field].decode('utf-8')
        sku3 = fix_sku(sku2, sku1)
        if sku3:
            whitelist.add(sku3)
            product_list[sku3] = row[desc_field].decode('utf-8')

    return whitelist, product_list


def match_sku(a, whitelist, product_list, brand):
    """
    >>> whitelist = ['TS5800D0808-EU', 'TS5800D1608-EU']
    >>> product_list = dict([(x, x) for x in whitelist])
    >>> match_sku('fets5800d0808-eu', whitelist, product_list, '')
    'FETS5800D0808-EU'
    """
    if a in whitelist:
        return a
    if a.upper() in whitelist:
        return a.upper()
    plain_a = a.replace('-', '').replace('/', '').lower()
    plain_a = plain_a[2:] if plain_a.startswith('fe') else plain_a
    for b in whitelist:
        plain_b = b.replace('-', '').replace('/', '').lower()
        plain_b = plain_b[2:] if plain_b.startswith('fe') else plain_b
        if plain_a.startswith(plain_b) or plain_b.startswith(plain_a):
            for brand_part in brand.split(' '):
                if brand_part.replace('-', '').upper() in product_list[b].replace('-', '').upper():
                    if a.lower().startswith('fe'):
                        return 'FE' + b
                    else:
                        return b

    return False

from scrapy.spider import BaseSpider
from scrapy.http import Request

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT


class CommsBaseSpider(BaseSpider):
    def __init__(self, *args, **kwargs):
        super(CommsBaseSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.errors = []

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "4TVm9qF0"
        username = "comms_express"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_file = "Monitor.csv"

        file_path = HERE + '/monitor.csv'
        sftp.get(remote_file, file_path)

        self.log("Loaded file: %s" % remote_file)

        with open(file_path) as f:
            reader = csv.DictReader(f)

            self.rows = list(reader)
            self.log("Records found: %d" % len(self.rows))

        self.whitelist, self.product_list = get_whitelist(self.rows)
        self.collected = {}

    def spider_idle(self, spider):
        if spider != self: return
        if self.collected:
            self.crawler.engine.schedule(
                Request('http://' + self.allowed_domains[0],
                        callback=self.yield_product,
                        dont_filter=True,
                        meta={'dont_retry': True}),
                spider)
            raise DontCloseSpider('Found pending requests')

    def yield_product(self, response):
        for item in self.collected.values():
            yield item
        self.collected = None

    def yield_item(self, item):
        self.log('Product identifier: %s' % item['identifier'])
        match = match_sku(item.get('identifier').encode('utf'), self.whitelist, self.product_list, item.get('brand', ''))
        if match:
            item['identifier'] = match

            if item['identifier'] in self.collected:
                if item['price'] < self.collected[item['identifier']]['price']:
                    self.collected[item['identifier']] = item
            else:
                self.collected[item['identifier']] = item
        else:
            self.log('[%s] identifier not in whitelist: %s' % (item['url'], item['identifier']))

    def yield_item_with_metadata(self, item):
        self.log('Product manufacturers code: %s' % item['metadata']['manufacturers_no'])
        match = match_sku(item['metadata']['manufacturers_no'].encode('utf'), self.whitelist, self.product_list, item.get('brand', ''))
        if match:
            item['metadata']['manufacturers_no'] = match

            if item['metadata']['manufacturers_no'] in self.collected:
                if item['price'] < self.collected[item['metadata']['manufacturers_no']]['price']:
                    self.collected[item['metadata']['manufacturers_no']] = item
            else:
                self.collected[item['metadata']['manufacturers_no']] = item
        else:
            self.log('[%s] identifier not in whitelist: %s' % (item['url'], item['metadata']['manufacturers_no']))
