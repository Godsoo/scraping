"""
Name: eservices-pl-ceneo.pl
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
Ticket reference: https://www.assembla.com/spaces/competitormonitor/tickets/4190
"""


import os
import csv
import pandas as pd
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu
from product_spiders.config import DATA_DIR


HERE = os.path.abspath(os.path.dirname(__file__))


class CeneoPl(BaseSpider):
    name = 'eservices-pl-ceneo.pl'
    allowed_domains = ['ceneo.pl']
    start_urls = ['http://www.ceneo.pl/']

    rotate_agent = True

    def __init__(self, *args, **kwargs):
        super(CeneoPl, self).__init__(*args, **kwargs)

        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.categories_urls = []
        categories_filename = os.path.join(HERE, 'ceneo_categories.csv')
        if os.path.exists(categories_filename):
            with open(categories_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.categories_urls.append(
                        (row['Category'] + ',' + row['Sub-Category'],
                         row['URL']))

        # Prevent deletions
        self.new_ids = []
        self.try_deletions = True

    def _get_prev_crawl_filename(self):
        filename = None
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        return filename

    def spider_idle(self, spider):
        if self.try_deletions:
            self.try_deletions = False

            filename = self._get_prev_crawl_filename()
            if filename and os.path.exists(filename):
                old_products = pd.read_csv(filename, dtype=pd.np.str, encoding='utf-8')
                deletions = old_products[old_products['identifier'].isin(self.new_ids) == False]
                i = 0
                for ix_, row in deletions.iterrows():
                    i += 1
                    row = dict(row)
                    request = Request(row['url'],
                                      dont_filter=True,
                                      callback=self.parse_product,
                                      meta={'category': row['category'],
                                            'cookiejar': i})
                    self._crawler.engine.crawl(request, self)

    def start_requests(self):
        cookie_jar = 0
        for category_name, category_url in self.categories_urls:
            cookie_jar += 1
            meta = {
                'category': category_name.decode('utf-8'),
                'cookiejar': cookie_jar,
            }
            yield Request(category_url, meta=meta)


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        url_processing = lambda u: urljoin_rfc(base_url, u[-1]).split('#')[0].split('?')[0] if u else ''
        price_processing = lambda p: extract_price_eu(p[0])

        list_view_mode = hxs.select('//a[contains(@class, "enable-view") '
                                    'and contains(@class, "enable-list-view") '
                                    'and not(contains(@class, "active"))]/@href').extract()
        if list_view_mode:
            yield Request(url_processing(list_view_mode),
                          meta={'category': response.meta['category'],
                                'cookiejar': response.meta['cookiejar']})
            return

        last_page_no = int(response.meta.get('last_page_no', 0))
        if not last_page_no:
            last_page_no = hxs.select('//input[@id="page-counter"]/@data-pagecount').extract()
            last_page_no = int(last_page_no[0] if last_page_no else 0)
        current_page_no = hxs.select('//input[@id="page-counter"]/@data-currentpage').extract()
        current_page_no = int(current_page_no[0] if current_page_no else 0)

        is_last_page = (current_page_no == last_page_no)
        next_page = hxs.select('//li[contains(@class, "page-arrow") and contains(@class, "arrow-next")]//a/@href').extract()
        if next_page:
            yield Request(url_processing(next_page),
                          meta={'category': response.meta['category'],
                                'cookiejar': response.meta['cookiejar'],
                                'last_page_no': last_page_no})

        products = hxs.select('//div[contains(@class, "category-list-body")]'
                              '/div[@data-pid and contains(@class, "cat-prod-row")]')
        for product_xs in products:
            loader = ProductLoader(item=Product(), selector=product_xs)
            loader.add_xpath('name', './/strong[contains(@class, "cat-prod-row-name")]//a/text()')
            loader.add_xpath('identifier', '@data-pid')
            loader.add_xpath('sku', '@data-pid')
            loader.add_xpath('url', './/strong[contains(@class, "cat-prod-row-name")]//a/@href', url_processing)
            loader.add_xpath('price', './/strong[contains(@class, "price")]/text()', price_processing)
            loader.add_value('category', response.meta['category'].split(','))
            loader.add_xpath('image_url', './/div[contains(@class, "cat-prod-row-foto")]//img[@data-original]'
                             '/@data-original|.//div[contains(@class, "cat-prod-row-foto")]//img/@src',
                             url_processing)
            item = loader.load_item()
            if item['identifier'] not in self.new_ids:
                self.new_ids.append(item['identifier'])
                yield item

        if ((not products) and (not next_page)) or ((not is_last_page) and (not next_page)):
            blocked_url = url_query_parameter(response.url, 'returnUrl')
            if blocked_url:
                blocked_url = urljoin_rfc(base_url, blocked_url)
                self.log('ERROR: Blocked URL => %s' % blocked_url)
            else:
                self.log('ERROR: No products or no next page in => %s' % response.url)
            retry_no = int(response.meta.get('retry_no', 0))
            if retry_no < 10:
                retry_no += 1
                self.log('DEBUG: Retrying page - Retry No: %s' % retry_no)
                yield Request(blocked_url or response.url,
                              meta={'category': response.meta['category'],
                                    'cookiejar': response.meta['cookiejar'],
                                    'retry_no': retry_no,
                                    'last_page_no': last_page_no},
                              dont_filter=True)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        price_decimal = None
        try:
            price_decimal = min(map(lambda p: Decimal(p),
                                    hxs.select('//section[@class="product-offers-group"]//tr/@data-offer-price')
                                    .extract()))
        except:
            price = hxs.select('//*[@itemprop="price"]/text()|//*[@itemprop="lowprice"]/text()').extract()
            price_decimal = extract_price_eu(price[0]) if price else None
        unavailable = 'Aktualnie brak ofert tego produktu. Zobacz inne produkty z kategorii' in response.body
        if (not price_decimal) and (not unavailable):
            blocked_url = url_query_parameter(response.url, 'returnUrl')
            if blocked_url:
                blocked_url = urljoin_rfc(base_url, blocked_url)
                self.log('ERROR: Blocked URL => %s' % blocked_url)
            else:
                self.log('ERROR: No product found in => %s' % response.url)
            retry_no = int(response.meta.get('retry_no', 0))
            if retry_no < 10:
                retry_no += 1
                self.log('DEBUG: Retrying page - Retry No: %s' % retry_no)
                yield Request(blocked_url or response.url,
                              meta={'category': response.meta['category'],
                                    'cookiejar': response.meta['cookiejar'],
                                    'retry_no': retry_no},
                              dont_filter=True,
                              callback=self.parse_product)
            return

        if price_decimal:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
            loader.add_xpath('identifier', '//input[@name="ProductID"]/@value')
            loader.add_xpath('sku', '//input[@name="ProductID"]/@value')
            loader.add_value('url', response.url)
            loader.add_value('price', price_decimal)
            loader.add_value('category', response.meta['category'].split(','))
            image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]).split('?')[0])

            item = loader.load_item()

            if item['identifier'] not in self.new_ids:
                self.new_ids.append(item['identifier'])
                yield item

    def proxy_service_check_response(self, response):
        return 'Captcha/Add?' in response.url
