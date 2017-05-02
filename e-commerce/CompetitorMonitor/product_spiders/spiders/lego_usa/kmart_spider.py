import os
import csv
import re
import json

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from product_spiders.config import DATA_DIR

HERE = os.path.abspath(os.path.dirname(__file__))


class KmartSpider(BaseSpider):
    name = 'legousa-kmart.com'
    allowed_domains = ['kmart.com']
    start_urls = ('http://www.kmart.com/service/search/productSearch?catalogId=10104&catgroupId=26053&catgroupIdPath=20007_20102_26053&filter=Brand%7CLEGO%7CLEGO%26%23174%3B+DUPLO%26%23174%3B&keyword=lego&levels=Toys+%26+Games_Blocks+%26+Building+Sets_Building+Sets&primaryPath=Toys+%26+Games_Blocks+%26+Building+Sets_Building+Sets&searchBy=subcategory&storeId=10151&tabClicked=All',)
    _re_sku = re.compile('(\d\d\d\d\d?)')

    handle_httpstatus_list = [403]

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'kmart_map_deviation.csv')
    # map_screenshot_method = 'scrapy_response'

    product_ajax_url = 'http://www.kmart.com/content/pdp/config/products/v1/products/%(pid)s?site=kmart'
    price_ajax_url = 'http://www.kmart.com/content/pdp/products/pricing/v1/get/price/display/json?pid=%(pid)s&pidType=0&priceMatch=Y&memberStatus=G&storeId=10151'

    def __init__(self, *args, **kwargs):
        super(KmartSpider, self).__init__(*args, **kwargs)

        # Errors
        self.errors = []

        self.map_screenshot_html_files = {}

    def start_requests(self):
        yield Request('http://www.kmart.com/', self.parse_default)

    def parse_default(self, response):

        if hasattr(self, 'prev_crawl_id'):
            with open(os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row['url']
                    pid_re = re.search(r'/p-(.*P)?', url.split('?')[0])
                    if pid_re:
                        price_url = self.price_ajax_url % {'pid': pid_re.group(1)[:-1]}
                        yield Request(price_url, callback=self.parse_price, meta={'product': row})

        # Scrape start urls
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        page = response.meta.get('page', 2)
        found = False

        data = json.loads(response.body)
        for p in data['products']:
            found = True
            url = p['url']
            pid_re = re.search(r'p-(.*P)?', url)
            if pid_re:
                product_url = self.product_ajax_url % {'pid': pid_re.group(1)}
                yield Request(product_url, callback=self.parse_product)

        if found:
            yield Request(self.start_urls[0] + '&pageNum=' + str(page), meta={'page':page+1})

    def parse_product(self, response):
        base_url = get_base_url(response)
        data = json.loads(response.body)

        product_data = {}

        product_data['name'] = data['data']['product']['name']
        if not product_data['name'].startswith('LEGO'):
            product_data['name'] = 'LEGO ' + product_data['name']
        product_data['identifier'] = data['data']['product']['id']
        product_data['category'] = data['data']['product']['taxonomy']['web']['sites']['kmart']['hierarchies'][0]['specificHierarchy'][-1]['name']
        product_data['sku'] = data['data']['product']['mfr']['modelNo']
        product_data['brand'] = data['data']['product']['brand']['name']
        product_data['url'] = urljoin_rfc(base_url, data['data']['product']['seo']['url']) + '/p-%s' % data['data']['product']['id']
        product_data['image_url'] = data['data']['product']['assets']['imgs'][1]['vals'][0]['src']

        price_url = self.price_ajax_url % {'pid': product_data['identifier'][:-1]}
        yield Request(price_url, callback=self.parse_price, meta={'product': product_data})

    def parse_price(self, response):
        data = json.loads(response.body)

        product_data = response.meta['product']

        product_price = str(data['priceDisplay']['response'][0]['finalPrice']['numeric'])

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', product_data['identifier'].decode('utf-8'))
        loader.add_value('name', product_data['name'].decode('utf-8'))
        loader.add_value('sku', product_data['sku'].decode('utf-8'))
        loader.add_value('url', product_data['url'].decode('utf-8'))
        loader.add_value('category', product_data['category'].decode('utf-8'))
        loader.add_value('brand', product_data['brand'].decode('utf-8'))
        loader.add_value('image_url', product_data['image_url'].decode('utf-8'))
        loader.add_value('price', product_price)

        yield loader.load_item()

    def _save_html_response(self, response, identifier):
        filename = os.path.join(HERE, 'kmart_%s.html' % identifier)
        with open(filename, 'w') as f_html:
            f_html.write(response.body)
        self.map_screenshot_html_files[identifier] = filename
