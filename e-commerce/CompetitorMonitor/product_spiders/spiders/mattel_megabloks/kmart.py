import os
import re
import datetime
import csv
import json
import shutil
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
from urlparse import urljoin as urljoin_rfc
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from hamiltonitems import HamiltonMeta, ReviewLoader, Review

from scrapy import log

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

HERE = os.path.abspath(os.path.dirname(__file__))


class MattelMegabloksKmartSpider(BaseSpider):
    name = 'mattel_megabloks-kmart.com'
    allowed_domains = ['www.kmart.com']
    start_urls = ('http://www.kmart.com/search=mattel',)

    handle_httpstatus_list = [403]

    def __init__(self, *args, **kwargs):
        super(MattelMegabloksKmartSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        if os.path.exists(os.path.join(HERE, 'kmart_products.csv')):
            shutil.copy(os.path.join(HERE, 'kmart_products.csv'),
                        os.path.join(HERE, 'kmart_products.csv.bak'))

    def spider_closed(self, spider):
        shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'kmart_products.csv'))

    # def start_requests(self):
    #     yield Request('http://www.kmart.com/', self.parse_default)
    #
    # def parse_default(self, response):
    #     if os.path.exists(os.path.join(HERE, 'kmart_products.csv')):
    #         with open(os.path.join(HERE, 'kmart_products.csv')) as f:
    #             reader = csv.DictReader(f)
    #             for row in reader:
    #                 yield Request(row['url'], self.parse_product, meta={'brand': row['brand']})
    #
    #     # Scrape start urls
    #     for url in self.start_urls:
    #         yield Request(url)

    def start_requests(self):
        search = ['mattel',
                  'barbie',
                  'hot+wheels',
                  'monster+high',
                  'disney+princess',
                  'max+steel',
                  'ever+after+high',
                  'matchbox',
                  'little+mommy',
                  'cars',
                  'polly+pocket',
                  'dc+universe',
                  'sofia+the+first',
                  'planes',
                  'toy+story',
                  'fijit+friends']
        brand = 'Mattel'
        for term in search:
            url = 'http://www.kmart.com/service/search/productSearch?catalogId=10104&keyword=' + term + '&searchBy=keyword&storeId=10151&tabClicked=All&vDropDown=All+Verticals'
            yield Request(url, callback=self.parse_category, dont_filter=True, meta={'brand': brand})
        search = ['mega+bloks',
                  "assassin's+creed",
                  'call+of+duty',
                  'cat',
                  "create+'n+play",
                  "create+'n+play+junior",
                  'dora+the+explorer',
                  'first+builders',
                  'halo',
                  'hello+kitty',
                  'jeep',
                  'john+deere',
                  'kapow',
                  'mega+play',
                  'power+rangers',
                  'ride-ons',
                  'ride+ons',
                  'skylanders',
                  'spongebob+squarepants',
                  'thomas+and+friends',
                  'world+builders']
        brand = 'Mega Bloks'
        for term in search:
            url = 'http://www.kmart.com/service/search/productSearch?catalogId=10104&keyword=' + term + '&searchBy=keyword&storeId=10151&tabClicked=All&vDropDown=All+Verticals'
            yield Request(url, callback=self.parse_category, dont_filter=True, meta={'brand': brand})

    def parse_category(self, response):
        base_url = get_base_url(response)
        brand = response.meta.get('brand')

        if response.body:
            data = json.loads(response.body)
            data = data['data']
            products = data['products']
            pagination = data['pagination']
            for product in products:
                identifier = product['sin']
                product_url = "http://www.kmart.com/content/pdp/config/products/v1/products/%s?site=kmart"
                yield Request(product_url % identifier, callback=self.parse_product, 
                              meta={'brand': brand, 'url': urljoin_rfc(base_url, product['url']), 'identifier': identifier})
            for page in pagination:
                if page['id'] != 1:
                    yield Request(add_or_replace_parameter(response.url, 'pageNum', str(page['id'])), callback=self.parse_category, meta={'brand': brand})
        else:
            self.log('WARNING: No results for %s' % brand)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        brand = response.meta.get('brand')
        identifier = response.meta.get('identifier')
        url = response.meta.get('url')

        data = json.loads(response.body)
        
        loader = ProductLoader(item=Product(), response=response)
        '''
        identifier = hxs.select('//input[@id="partnumber"]/@value').extract()
        if not identifier:
            identifier = hxs.select('//input[@name="bundlePID"]/@value').extract()
        if not identifier:
            pdp_redirect = url_query_parameter(response.url, 'PDP_REDIRECT')
            if pdp_redirect == 'false':
                retry = int(response.meta.get('retry', 0)) + 1
                if retry < 50:
                    yield Request(response.url,
                                  callback=self.parse_product,
                                  meta={'retry': retry, 'brand': brand},
                                  dont_filter=True)
            else:
                url = add_or_replace_parameter(response.url, 'PDP_REDIRECT', 'false')
                yield Request(url, callback=self.parse_product, dont_filter=True, meta={'brand': brand})
            return
        '''
        name = data['data']['product']['name']
        if not name:
            return
        try:
            sku = data['data']['product']['mfr'].get('modelNo', '')
        except KeyError:
            sku = ''
        category = [category['name'] for category in data['data']['productmapping']['primaryWebPath']]
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('url', url)
        '''
        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        if not price:
            price = hxs.select('//span[@class="mapPrice setOne"]/text()').extract()
            if not price:
                price = hxs.select('//*[@id="p0_price"]//span[@class="pricing"]/text()').extract()
        price = price[0] if price else ''
        loader.add_value('price', price)
        '''
        image_url = data['data']['product']['assets']['imgs'][0]['vals'][0]['src']
        if image_url:
            loader.add_value('image_url', image_url)

        product = loader.load_item()
        metadata = HamiltonMeta()
        metadata['brand'] = brand.strip().lower()
        metadata['reviews'] = []
        product['metadata'] = metadata
        # catalog_id = hxs.select('//*[@id="catalogId"]/@value').extract()[0]
        price_url = "http://www.kmart.com/content/pdp/products/pricing/v1/get/price/display/json?pid=%(product_id)s&pidType=0&priceMatch=Y&memberStatus=G&storeId=10151"
        yield Request(price_url % {'product_id': identifier.replace('P', '')},
                      meta={'product': product},
                      callback=self.parse_price)

    def parse_price(self, response):
        data = json.loads(response.body)
        meta = response.meta
       
        product = meta['product']
        product['price'] = 0
        try:
            product['price'] = data['priceDisplay']['response'][0]['prices']['finalPrice']['min']
        except:
            if not meta.get('retry', False):
                price_url = add_or_replace_parameter(response.url, 'pidType', '3')
                price_url = add_or_replace_parameter(price_url, 'pid', product['identifier'])

                meta['retry'] = True
                log.msg('RETRY PRICE: ' + price_url)
                yield Request(price_url,
                              meta=meta,
                              callback=self.parse_price)
           

        reviews_url = 'http://www.kmart.com/content/pdp/ratings/single/search/Kmart/%(product_id)s&targetType=product&limit=1000&offset=0'
        yield Request(reviews_url % {'product_id': product['identifier']},
                      meta={'product': product},
                      callback=self.parse_reviews)

    def parse_reviews(self, response):
        data = json.loads(response.body)

        product = response.meta['product']

        reviews = data['data']['reviews']
        for review in reviews:
            review_loader = ReviewLoader(item=Review(), response=response, date_format="%B %d, %Y")
            review_date = datetime.datetime.strptime(review[u'published_date'], '%a, %b %d, %Y')
            review_loader.add_value('date', review_date.strftime("%B %d, %Y"))

            extra_text = []

            if review[u'recommended']:
                extra_text.append('I would recommend this product to a friend.')
            
            try:
                extra_text.append('%(city)s, %(state)s' % review[u'author'])
            except KeyError:
                pass
            if review[u'author'][u'isBuyer']:
                extra_text.append('Verified Purchase')

            full_text = review[u'content'] + ' #&#&#&# ' + '\n'.join(extra_text)
            if review[u'summary']:
                full_text = review[u'summary'].strip() + ' #&#&#&# ' + full_text
            review_loader.add_value('full_text', full_text)

            review_loader.add_value('rating', review[u'attribute_rating'][0][u'value'])
            review_loader.add_value('url', product['url'])
            product['metadata']['reviews'].append(review_loader.load_item())

        yield product
