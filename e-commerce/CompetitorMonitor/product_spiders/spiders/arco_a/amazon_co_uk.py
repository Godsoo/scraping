import os
import csv
import json
import cStringIO
from decimal import Decimal

from scrapy.http import Request
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.utils import extract_price
from product_spiders.items import Product
from product_spiders.spiders.BeautifulSoup import BeautifulSoup

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders.amazonspider2.scraper import AmazonUrlCreator
from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonProductLoader
from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider
from product_spiders.config import api_key
from product_spiders.utils import get_cm_api_root_for_spider

from scrapy import log


class ArcoAmazonCoUkSpider(BaseAmazonSpider, BigSiteMethodSpider):
    name = 'arco-new-amazon.co.uk'
    all_sellers = False
    only_buybox = True
    _use_amazon_identifier = True
    max_pages = 1
    parse_options = True
    collect_products_with_no_dealer = True

    do_retry = True

    category = 'A'

    website_id = 253
    member_id = 31

    allowed_domains = ['amazon.co.uk']
    start_urls = ['http://www.amazon.co.uk', ]

    new_system = True
    product_loader = AmazonProductLoader

    full_crawl_day = 6

    domain = 'amazon.co.uk'

    def __init__(self, *args, **kwargs):
        super(ArcoAmazonCoUkSpider, self).__init__(*args, **kwargs)
        # super(ArcoAmazonCoUkSpider, self).__init__('www.amazon.co.uk', *args, **kwargs)

        dispatcher.connect(self.spider_process_main, signals.spider_idle)

        self._collect = self._collect_all

        self.main_processed = False

    def _collect_all(self, new_item):
        collected = super(ArcoAmazonCoUkSpider, self)._collect_all(new_item)
        if collected:
            if new_item['identifier']:
                if new_item['identifier'] not in self.matched_identifiers:
                    self.matched_identifiers.add(new_item['identifier'])
            else:
                if new_item['name'] not in self.matched_identifiers:
                    self.matched_identifiers.add(new_item['name'])

    def extract_price(self, price):
        """
        override extract price, returns EXC VAT price
        """
        price = extract_price(price)
        return self.calculate_price(price)

    def calculate_price(self, value):
        if value:
            return round(value / Decimal('1.2'), 2)  # 20% EXC VAT
        else:
            return None

    def start_requests(self):
        return BigSiteMethodSpider.start_requests(self)

    def parse_full(self, response):
        raise NotImplementedError()

    def spider_process_main(self, spider):
        self.log("Spider idle 2")
        if spider.name == self.name:
            if self.full_run and not self.main_processed:
                request = Request(self.start_urls[0], dont_filter=True, callback=self.closing_parse_full)
                self._crawler.engine.crawl(request, self)
                self.main_processed = True

    def closing_parse_full(self, response):
        return BaseAmazonSpider.start_requests(self)

    def get_search_query_generator(self):
        with open(os.path.join(HERE, 'arco_products.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for row in reader:
                if row['category'].lower() == self.category.lower():
                    yield (row['description'].strip(), {
                        'sku': row['product'].strip().lower(),
                        'name': row['description'].strip(),
                        'category': '',
                        'price': row['price'].strip(),
                    })

    def _start_requests_full(self):
        self.matched = []
        self.matched_identifiers = set()
        url = '%(api_root)s/api/get_matches.csv?api_key=%(api_key)s&member_id=%(member_id)s&website_id=%(website_id)s' % \
              {'api_root': get_cm_api_root_for_spider(self), 'api_key': api_key,
               'member_id': self.member_id, 'website_id': self.website_id}
        log.msg("Loading matches and suggestions from new system: %s" % url)
        yield Request(
            url=url,
            callback=self.parse_csv,
            dont_filter=True
        )

    def get_url_from_asin(self, asin):
        return AmazonUrlCreator.build_url_from_asin(
                    self.domain,
                    asin,
                )

    def _create_product_match_request(self, response, product_info):
        url = self.get_url_from_asin(product_info['identifier'].split(':')[1])

        loader = AmazonProductLoader(item=Product(), response=response)
        loader.add_value('name', product_info['name'].strip())
        loader.add_value('identifier', product_info['identifier'].strip())
        loader.add_value('sku', product_info['sku'].strip().lower())
        loader.add_value('url', url)
        product = {
            'name': product_info['name'].strip(),
            'sku': product_info['sku'].strip().lower(),
            'identifier': product_info['identifier'].strip(),
            'url': url,
        }
        for add_field in ['image_url', 'brand', 'category', 'dealer']:
            if add_field in product_info:
                product[add_field] = product_info['' + add_field]
                loader.add_value(add_field, product_info['' + add_field])

        # self.matched.append(product)
        # self.matched_identifiers.add(product['identifier'].strip())

        return Request(
            url=url,
            callback=self.parse_product,
            meta={
                '_product': loader.load_item(),
                'search_item': product,
                'collected_items': [],
                'requests': [],
                'current_page': 1,
                'requests_done': set(),
                'check_price': True,
                'parse_options': True,
                'matches_search': True
            },
            dont_filter=True
        )

    def parse_csv(self, response):
        """
        Processes matches and suggestions from new system
        """
        reader = csv.DictReader(cStringIO.StringIO(response.body))

        reqs = []

        for prod in reader:
            for field in prod:
                prod[field] = prod[field].decode('utf-8', 'ignore')

            prod_info = {}
            for field, value in prod.items():
                if field.startswith('second_'):
                    prod_info[field.replace('second_', '')] = value

            reqs.append(self._create_product_match_request(response, prod_info))

        log.msg("Loaded %d matches and suggestions from new system" % len(reqs))

        for r in reqs:
            yield r

    # override for Big Site Method
    def parse_matches_new_system(self, response):
        """
        Processes matches from new system.
        Invokes product urls requests with callback to 'parse_product
        """
        products = json.loads(response.body)
        matches = products.get('matches', [])
        if not matches:
            self.errors.append('Big Site Method issue: matches not found')

        reqs = []
        for prod in matches:
            reqs.append(self._create_product_match_request(response, prod))

        log.msg("Loaded %d matches from new system" % len(reqs))

        for r in reqs:
            yield r

    def match(self, meta, search_item, new_item):
        if 'price' not in new_item or not new_item['price']:
            return False
        return True

    def _may_collect(self, collected_items, new_item):
        return True

    def collect_price(self, hxs, response):
        soup = BeautifulSoup(response.body)
        try:
            soup_form = soup.find(id='handleBuy')
            price = soup_form.find('b', 'priceLarge')
            if not price:
                price = soup_form.find('span', 'priceLarge')
            if not price:
                price = soup_form.find('span', 'price')
            if not price:
                price = soup_form.find('span', 'pa_price')
            if price:
                price = self.extract_price(price.text)
            else:
                price = None
        except:
            price = hxs.select('//div[@id="price"]//td[text()="Price:"]'
                               '/following-sibling::td/span/text()').extract()
            if not price:
                price = hxs.select('//span[@id="priceblock_saleprice"]/text()').extract()
            if not price:
                price = hxs.select('//span[@id="priceblock_ourprice"]/text()').extract()
            if not price:
                price = hxs.select('//span[@id="actualPriceValue"]/*[@class="priceLarge"]/text()').extract()

            if price:
                price = self.extract_price(price[0])
            else:
                price = None

        return price
