# -*- coding: utf-8 -*-

"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4824-transcat-|-tequipment-|-new-site/details#

Extract all products
"""

import os
import json
import pandas as pd
from urlparse import urljoin
from copy import deepcopy
from decimal import Decimal
from scrapy import Spider, Request
from scrapy.utils.url import add_or_replace_parameter
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from product_spiders.lib.spiderdata import SpiderData
from product_spiders.config import DATA_DIR
from product_spiders.config import new_system_api_roots as API_ROOTS
from product_spiders.config import api_key as API_KEY
from product_spiders.contrib.compmon2 import Compmon2API
from transcatitems import TranscatMeta, Review, ReviewLoader


class TEquipmentSpider(Spider):
    name = 'transcat-tequipment.net'
    allowed_domains = ['tequipment.net']
    start_urls = ['http://www.tequipment.net/departments/']
    base_url = 'http://www.tequipment.net'

    reviews_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                       'Accept-Encoding': 'gzip, deflate, sdch',
                       'Accept-Language': 'es-419,es;q=0.8,en;q=0.6',
                       'Connection': 'keep-alive',
                       'Host': 'www.tequipment.net',
                       'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:46.0) Gecko/20100101 Firefox/46.0',
                       'X-Requested-With': 'XMLHttpRequest'}
    reviews_url = 'http://www.tequipment.net/ajax/store/getcontrol.aspx?F=GetReviewPage&ItemId={item_id}&PageSize=10&pg={pg}&Order=2'

    cart_headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
    }
    cart_url = 'http://www.tequipment.net/ajax/store/ajax.aspx?F=Add2Cart&ItemId={item_id}' + \
               '&OrderItemId=0&Qty=1&Recipient=Myself&ValueId=0&MemberGroupId=0&UseMAPPrice=False&IgnoreCallBack=false&DisableSlider=false'

    def __init__(self, *args, **kwargs):
        super(TEquipmentSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        self.try_deletions = True
        self.matched_identifiers = self._get_matched_identifiers()
        self.matched_deletions = None

    def spider_idle(self, spider):
        if self.try_deletions and self.matched_identifiers:
            self.try_deletions = False
            filename = self._get_prev_crawl_filename()
            if filename and os.path.exists(filename):
                old_products = pd.read_csv(filename, dtype=pd.np.str, encoding='utf-8')
                if not old_products.empty:
                    matched_old_products = old_products[old_products['identifier'].isin(self.matched_identifiers)]
                    self.matched_deletions = matched_old_products[matched_old_products['identifier'].isin(self._new_ids) == False]
                    for req in self.start_matched_products_requests():
                        self.crawler.engine.crawl(req, self)

    def start_requests(self):
        self.init_cache()

        for url in self.start_urls:
            yield Request(url)

    def start_matched_products_requests(self):
        if self.matched_deletions is None:
            self.log('(!) => MATCHED PRODUCTS REQUESTS DIDN\'T START: `matched_deletions` is None')
            return
        self.log('=> MATCHED PRODUCTS REQUESTS STARTED')
        for ix_, row in self.matched_deletions.iterrows():
            row = dict(row)
            yield Request(row['url'],
                          dont_filter=True,
                          callback=self.parse_product,
                          meta={'category': row['category'],
                                'dont_merge_cookies': True})


    def _get_prev_crawl_filename(self):
        filename = None
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        return filename

    def _get_matched_identifiers(self):
        api_host = API_ROOTS['new_system']
        api_key = API_KEY
        compmon_api = Compmon2API(api_host, api_key)
        matched_products = compmon_api.get_matched_products(512)
        matched_identifiers = [p['identifier'] for p in matched_products]
        return matched_identifiers

    def init_cache(self):
        self._cache = {}
        sd = SpiderData(spider_name=self.name)
        f, reader = sd.get_prev_crawl_data_reader()
        for row in reader:
            self._cache[row['identifier']] = row
        f.close()

    def parse(self, response):
        departments = filter(lambda u: 'discontinued' not in u, response.xpath('//div[contains(@class,"listColumn")]/ul/h2/a/@href').extract())
        for url in departments:
            yield Request(response.urljoin(url), callback=self.parse_price_ranges)

    def parse_price_ranges(self, response):
        ranges = response.xpath('//*[@id="idevfacet_SalePrice"]//a/@href').extract()
        for url in ranges:
            url = response.urljoin(url)
            url = add_or_replace_parameter(url, 'perpage', '300')
            url = add_or_replace_parameter(url, 'F_Sort', '1')
            yield Request(url, callback=self.parse_product_list, meta={'dont_merge_cookies': True})


    def parse_product_list(self, response):
        next_page = response.xpath('//div[@class="paging"]//a[@rel="Next"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]),
                          callback=self.parse_product_list,
                          meta=response.meta)

        products = response.css('.itemList .itemWrapper')
        for product_xs in products:
            url = product_xs.xpath('.//h3/a/@href').extract_first()
            one_price = product_xs.css('.priceButtonText')
            call_us = bool(product_xs.css('#lnkCallUs'))
            if one_price or call_us:
                pid = product_xs.css('.hdnIdevItemId').xpath('@value').extract_first()
                item = self.load_cached_item(pid)
                if item is not None:
                    item['metadata'] = TranscatMeta()
                    item['metadata']['reviews'] = []

                    has_reviews = bool(product_xs.css('.readReviews'))
                    button_text = one_price.xpath('text()').extract_first()
                    if button_text and button_text.lower() == 'see price':
                        yield Request(self.cart_url.format(item_id=pid),
                                      callback=self.parse_add_to_cart_price,
                                      headers=self.cart_headers,
                                      meta={'items': [item],
                                            'identifier': pid,
                                            'has_reviews': has_reviews,
                                            'dont_merge_cookies': True})
                    else:
                        price = product_xs.css('.sale::text').re_first(r'[\d\.,]+')
                        item['price'] = Decimal(price.replace(',', '')) if price else Decimal('0')
                        strike = product_xs.css('.listPrice .strike::text').extract_first()
                        item['metadata']['strike'] = strike.strip() if strike else ''
                        if has_reviews:
                            yield self.get_reviews_request(pid, [item])
                        else:
                            yield item
                    continue
            yield Request(response.urljoin(url),
                          callback=self.parse_product,
                          meta=response.meta)

    def load_cached_item(self, pid):
        item = None
        r = self._cache.get(pid)
        if r is not None:
            loader = ProductLoader(item=Product(), response=None)
            loader.add_value('identifier', pid)
            for k in ['sku', 'name', 'url', 'category', 'brand', 'image_url']:
                loader.add_value(k, r[k].decode('utf-8'))
            if r['stock']:
                loader.add_value('stock', int(r['stock']))
            item = loader.load_item()
        return item

    def get_reviews_request(self, identifier, items):
        return Request(self.reviews_url.format(item_id=identifier, pg='1'),
                       callback=self.parse_review,
                       headers=self.reviews_headers,
                       cookies={},
                       meta={'items': items,
                             'identifier': identifier,
                             'page': 1,
                             'dont_merge_cookies': True})

    def parse_product(self, response):
        loader = ProductLoader(response=response, item=Product())

        loader.add_value('url', response.url)

        name = response.xpath('//div[@class="pageHeading detailsHeading"]/h1[@class="hdng"]/text()').extract()
        loader.add_value('name', name)

        price = response.xpath('//div[@class="salePrice"]/span[@class="sale"]/text()').extract()
        if not price:
            price = response.xpath('//div[@class="defaultPrice"]/span[@class="sale"]/text()').extract()
        if price:
            loader.add_value('price', price)
        else:
            loader.add_value('price', '0.00')

        categories = response.xpath('//div[@class="breadcrumbs"]//span[@itemprop="title"]/text()')[1:-1].extract()
        for category in categories:
            loader.add_value('category', category)

        sku = response.xpath('//div[@class="breadcrumbs"]//span[@itemprop="title"]/text()')[-1].extract()
        loader.add_value('sku', sku)

        identifier = response.xpath('//script[contains(text(),"reviewPage")]/text()').re_first('ItemId=(\d+)&')
        loader.add_value('identifier', identifier)

        image_url = response.xpath('//img[@class="mainImage"]/@src').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))

        loader.add_value('brand', categories[-1])

        item = loader.load_item()
        item['metadata'] = TranscatMeta()
        item['metadata']['reviews'] = []
        strike = response.xpath('//div[@class="listPrice"]/span[@class="strike"]/text()').extract()
        item['metadata']['strike'] = strike[0].strip() if strike else ''

        items = []
        options = response.xpath('//table[@id="tblChildren"]//tr')[1:]
        for option in options:
            option_name = option.select('.//p[@class="itemDesc"]/text()').extract()
            option_sku = option.select('.//p[@class="itemDesc"]/../strong/text()').extract()
            option_name = option_name[0].replace('-', ' ').strip() if option_name else ''
            option_price = option.select('.//span[contains(@id,"defaultPriceDisplay")]/text()').extract()
            if 'Discontinued' in option_price or not option_price:
                continue
            option_id = option.select('.//input[contains(@id,"chkItemCompare")]/@value')[0].extract()
            p = deepcopy(item)
            p['identifier'] += u'-{}'.format(option_id)
            p['price'] = extract_price(option_price[0]) if option_price else '0.00'
            p['name'] += u' {}'.format(option_name)
            p['name'] = p['name'].strip()
            if option_sku:
                p['sku'] = option_sku[0].lower().strip()
            strike = option.select('.//span[@class="strike"]/text()').extract()
            p['metadata']['strike'] = strike[0].strip() if strike else ''
            items.append(p)
        if not options:
            items.append(item)

        multi_options_link = response.xpath('//a[contains(@id,"ViewAllCombinations")]/@href').extract()
        has_reviews = bool(response.xpath('//span[@class="TotalReviewsCount" and text()!="0"]'))

        if multi_options_link:
            yield Request(response.urljoin(multi_options_link[0]),
                          cookies={},
                          meta={'items': items,
                                'has_reviews': has_reviews,
                                'identifier': identifier,
                                'dont_merge_cookies': True},
                          callback=self.parse_multi_options)
            return

        add_to_cart_price = 'see price' in map(unicode.lower, response.xpath('//span[@class="priceButtonText"]/text()').extract())
        if add_to_cart_price:
            yield Request(self.cart_url.format(item_id=identifier),
                          callback=self.parse_add_to_cart_price,
                          headers=self.cart_headers,
                          meta={'items': items,
                                'identifier': identifier[0],
                                'has_reviews': has_reviews,
                                'dont_merge_cookies': True})

        if has_reviews:
            yield self.get_reviews_request(identifier, items)
        else:
            for item in items:
                yield item

    def parse_multi_options(self, response):
        items = response.meta.get('items')
        options = response.xpath('//table[@class="results table-sort table-noscroll"]//tr')[1:]
        identifier = response.meta.get('identifier')
        has_reviews = response.meta.get('has_reviews')
        items_with_options = []
        for item in items:
            for option in options:
                p = deepcopy(item)
                option_identifier = option.xpath('.//span[@class="itemName"]/a/@href').re('s=\[(.*)\]')
                option_name = option.xpath('//span[@class="itemName"]/a/text()').extract()
                option_price = option.xpath('.//td[@class="price"]/span/text()').extract()
                if 'Discontinued' in option_price or not option_price:
                    continue
                p['identifier'] += u'-{}'.format(option_identifier[0])
                p['price'] = extract_price(option_price[-1])
                p['name'] += u' {}'.format(option_name[0])
                p['name'] = p['name'].strip()
                items_with_options.append(p)
        if has_reviews:
            yield self.get_reviews_request(identifier, items_with_options)
        else:
            for item in items_with_options:
                yield item

    def parse_add_to_cart_price(self, response):
        data = json.loads(response.body)
        for item in response.meta['items']:
            item['price'] = extract_price(data['Price'])
            if not response.meta['has_reviews']:
                yield item
        if response.meta['has_reviews']:
            yield self.get_reviews_request(response.meta['identifier'], response.meta['items'])

    def parse_review(self, response):
        items = response.meta.get('items')
        identifier = response.meta.get('identifier')
        data = json.loads(response.body)
        page = response.meta.get('page')
        for review in data['Reviews']:
            review_loader = ReviewLoader(item=Review(), response=response, date_format='%b %d, %Y')

            review_loader.add_value('date', review['CreateDate'])

            title = review['Title']
            comment = review['Comment']
            full_text = u'{}\n{}'.format(title, comment)
            review_loader.add_value('full_text', full_text)

            rating = int(float(review['Rating']))
            review_loader.add_value('rating', rating)

            url = urljoin(self.base_url, review['PermaLink'])
            review_loader.add_value('url', url)
            for item in items:
                item['metadata']['reviews'].append(review_loader.load_item())
        if page < data['NumPages']:
            yield Request(self.reviews_url.format(item_id=identifier, pg=str(page + 1)),
                          callback=self.parse_review,
                          headers=self.reviews_headers,
                          meta={'items': items,
                                'identifier': identifier,
                                'page': page + 1,
                                'dont_merge_cookies': True})
        else:
            for item in items:
                yield item
