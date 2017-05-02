"""
Name: ballicom.co.uk
Account: MCI Diventi

IMPORTANT

PLEASE DON'T ENABLE BSM HERE:

The reason is that this site has a lot of matched products

Consider the following:

- This spider is blocked, please be careful
- At the moment Tor works well here. It's using SOCKS proxy list from Proxy Service
  [NOTE 2016-05-31: Tor doesn't work anymore]
- This spider uses a "custom BSM" which works as follow:
  1. First picks up products from brand lists.
     [NOTE 2016-05-31: only once a month]
     [NOTE 2016-06-12: only for selected brands (see ticket #4839)]
  2. Then it calculates deletions and goes to missing matched product pages
  3. Then copies the data from previous crawl for missing products
- This works that way because the website has a lot of products which does not show in its product lists

"""


import os
import pandas as pd

from scrapy import Spider, Request
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from product_spiders.config import DATA_DIR
from product_spiders.config import new_system_api_roots as API_ROOTS
from product_spiders.config import api_key as API_KEY
from product_spiders.contrib.compmon2 import Compmon2API
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher


class BallicomSpider(Spider):
    name = 'ballicom.co.uk'
    allowed_domains = ['ballicom.co.uk']
    start_urls = [
        'https://www.ballicom.co.uk/manufacturers/hewlett-packard-enterprise.104952/?page_count=200&sort=price-asc&manufacturers_id=104952',
        'https://www.ballicom.co.uk/manufacturers/huawei.103111/?page_count=200&sort=price-asc&manufacturers_id=103111',
        'https://www.ballicom.co.uk/manufacturers/cisco.104392/?page_count=200&sort=price-asc&manufacturers_id=104392',
        'https://www.ballicom.co.uk/manufacturers/hp.102550/?page_count=200&sort=price-asc&manufacturers_id=102550',
        'https://www.ballicom.co.uk/manufacturers/juniper.102981/?page_count=200&sort=price-asc&manufacturers_id=102981',
        'https://www.ballicom.co.uk/manufacturers/apc.104354/?page_count=200&sort=price-asc&manufacturers_id=104354',
        'https://www.ballicom.co.uk/manufacturers/avaya.104364/?page_count=200&sort=price-asc&manufacturers_id=104364',
        'https://www.ballicom.co.uk/manufacturers/barracuda.104373/?page_count=200&sort=price-asc&manufacturers_id=104373',
        'https://www.ballicom.co.uk/manufacturers/brocade.104382/?page_count=200&sort=price-asc&manufacturers_id=104382',
        'https://www.ballicom.co.uk/manufacturers/lenovo.102712/?page_count=200&sort=price-asc&manufacturers_id=102712',
        'https://www.ballicom.co.uk/manufacturers/microsoft.102314/?page_count=200&sort=price-asc&manufacturers_id=102314',
        'https://www.ballicom.co.uk/manufacturers/mitel.103629/?page_count=200&sort=price-asc&manufacturers_id=103629',
        'https://www.ballicom.co.uk/manufacturers/moxa-technologies.103735/?page_count=200&sort=price-asc&manufacturers_id=103735',
        'https://www.ballicom.co.uk/manufacturers/nortel.103750/?page_count=200&sort=price-asc&manufacturers_id=103750',
        'https://www.ballicom.co.uk/manufacturers/powerdsine.100132/?page_count=200&sort=price-asc&manufacturers_id=100132',
        'https://www.ballicom.co.uk/manufacturers/vmware.389/?page_count=200&sort=price-asc&manufacturers_id=389',
        'https://www.ballicom.co.uk/manufacturers/3com.100047/?page_count=200&sort=price-asc&manufacturers_id=100047',
        'https://www.ballicom.co.uk/manufacturers/3comm.100873/?page_count=200&sort=price-asc&manufacturers_id=100873',
        'https://www.ballicom.co.uk/manufacturers/eaton.104446/?page_count=200&sort=price-asc&manufacturers_id=104446',
        'https://www.ballicom.co.uk/manufacturers/emerson.102967/?page_count=200&sort=price-asc&manufacturers_id=102967',
        'https://www.ballicom.co.uk/manufacturers/emulex.328/?page_count=200&sort=price-asc&manufacturers_id=328',
        'https://www.ballicom.co.uk/manufacturers/extreme-networks.104851/?page_count=200&sort=price-asc&manufacturers_id=104851',
        'https://www.ballicom.co.uk/manufacturers/fujitsu.104464/?page_count=200&sort=price-asc&manufacturers_id=104464',
        'https://www.ballicom.co.uk/manufacturers/nokia.100188/?page_count=200&sort=price-asc&manufacturers_id=100188',
        'https://www.ballicom.co.uk/manufacturers/seagate.102160/?page_count=200&sort=price-asc&manufacturers_id=102160',
        'https://www.ballicom.co.uk/manufacturers/west-dig.103242/?page_count=200&sort=price-asc&manufacturers_id=103242',
        'https://www.ballicom.co.uk/manufacturers/hewlett-packard.102934/?page_count=200&sort=price-asc&manufacturers_id=102934',
    ]

    rotate_agent = True
    download_timeout = 5

    custom_settings = {
        'RETRY_TIMES': 20,
    }

    full_month_day = 0  # All days

    def __init__(self, *args, **kwargs):
        super(BallicomSpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self._new_ids = []
        self.try_deletions = False
        self.copy_previous_data = False
        self.matched_identifiers = self._get_matched_identifiers()
        self.matched_deletions = None
        self.unmatched_deletions = None
        self.home_url = 'https://www.ballicom.co.uk'

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, callback=self.parse_products)

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
        elif self.copy_previous_data:
            self.copy_previous_data = False
            filename = self._get_prev_crawl_filename()
            if filename and os.path.exists(filename):
                old_products = pd.read_csv(filename, dtype=pd.np.str, encoding='utf-8')
                if not old_products.empty:
                    self.unmatched_deletions = old_products[old_products['identifier'].isin(self._new_ids) == False]
                    req = Request('file://' + filename,
                                  meta={'dont_redirect': True,
                                        'handle_httpstatus_all': True},
                                  callback=self.copy_unmatched_deletions,
                                  dont_filter=True)
                    self.crawler.engine.crawl(req, self)

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

    def _parse_sitemap(self, response):
        i = 0
        for req in super(BallicomSpider, self)._parse_sitemap(response):
            if not 'sitemap' in req.url:
                i += 1
                url = req.url.replace('http://', 'https://')
                url = add_or_replace_parameter(url, 'page_count', '200')
                new_req = req.replace(url=url)
                new_req.meta['dont_merge_cookies'] = True
                yield new_req
            else:
                yield req

    def start_matched_products_requests(self):
        if self.matched_deletions is None:
            self.log('(!) => MATCHED PRODUCTS REQUESTS DIDN\'T START: `matched_deletions` is None')
            return
        self.log('=> MATCHED PRODUCTS REQUESTS STARTED')
        i = 0
        for ix_, row in self.matched_deletions.iterrows():
            i += 1
            row = dict(row)
            yield Request(row['url'],
                          dont_filter=True,
                          callback=self.parse_product,
                          meta={'category': row['category'],
                                'dont_merge_cookies': True})

    def copy_unmatched_deletions(self, response):
        if self.unmatched_deletions is None:
            return
        self.log('=> COPYING UNCOLLECTED PREVIOUS DATA')
        for ix_, row in self.unmatched_deletions.iterrows():
            row = dict(row)
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', row['identifier'])
            loader.add_value('sku', row['sku'] or '')
            loader.add_value('name', row['name'])
            loader.add_value('url', row['url'])
            if row['image_url']:
                loader.add_value('image_url', row['image_url'])
            loader.add_value('category', row['category'] or '')
            loader.add_value('brand', row['brand'] or '')
            if row['stock']:
                if int(row['stock']) == 0:
                    continue
                loader.add_value('stock', row['stock'])
            loader.add_value('price', row['price'])
            loader.add_value('shipping_cost', row['shipping_cost'])
            yield loader.load_item()

    def parse_nothing(self, response):
        # Nothing, pass to next step in spider_idle
        return

    def parse_products(self, response):
        brand = response.xpath('//ul[@class="breadcrumb"]/li[@class="active"]//text()').extract()
        products = response.xpath('//ul[@class="product-listing"]/li')
        for product_xs in products:
            identifier = product_xs.xpath('.//h6[@class="mpn" and contains(text(), "QuickCode")]//text()').re(r'\d+')
            sku = map(unicode.strip, product_xs.xpath('.//h6[@class="mpn" and contains(text(), "MPN")]/span/text()').extract())
            name = product_xs.xpath('.//h3/text()').extract()
            url = map(lambda u: response.urljoin(u), product_xs.xpath('.//a/@href').extract())
            image_url = map(lambda u: response.urljoin(u), product_xs.xpath('.//div[contains(@class, "img-container")]//img/@src').extract())
            stock = product_xs.xpath('.//*[contains(text(), "Qty Available:")]/text()').re(r'(\d+)')
            price = product_xs.xpath('.//div[@class="price"]/text()').re(r'[\d,.]+')
            if identifier and price:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('identifier', identifier[0])
                loader.add_value('sku', sku[0])
                loader.add_value('name', name[0])
                loader.add_value('url', url[0])
                if image_url:
                    loader.add_value('image_url', image_url[0])
                loader.add_value('category', brand[0])
                loader.add_value('brand', brand[0])
                if stock:
                    if int(stock[0]) == 0:
                        continue
                    loader.add_value('stock', stock[0])
                loader.add_value('price', price[0])
                loader.add_value('shipping_cost', '4.16')
                item = loader.load_item()
                if item['identifier'] not in self._new_ids:
                    self._new_ids.append(item['identifier'])
                    yield item

        next_page = response.xpath('//div[@class="pagination"]//span[@class="caret-right"]/parent::a/@href').extract()
        if next_page:
            url = response.urljoin(next_page[0])
            yield Request(url,
                          meta={'dont_merge_cookies': True},
                          callback=self.parse_products)

    def parse_product(self, response):
        try:
            identifier = response.xpath('//li[span[1]="Ballicom ID"]/span[2]/text()').extract()[0].strip()
        except:
            return

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier)
        loader.add_xpath('sku', '//span[@itemprop="mpn"]/text()')
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')

        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        if price:
            price = extract_price(price[0].strip())
            loader.add_value('price', price)
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = response.urljoin(image_url[0])
            if len(image_url) <= 255:
                loader.add_value('image_url', image_url)
        brand = response.xpath('//div[@id="detail_tabbar"]//h4/text()').extract()
        if brand:
            loader.add_value('brand', brand[0].strip())
            loader.add_value('category', brand[0].strip())
        loader.add_value('shipping_cost', '4.16')
        stock = response.xpath('//li[span[1]="Qty Available"]/span[2]/text()').re(r'(\d+)')
        if not stock:
            stock = response.xpath('//li[span[1]="Qty Available"]/span[2]/text()').extract()
        if stock:
            if int(stock[0]) == 0:
                return
            loader.add_value('stock', stock[0].strip())
        item = loader.load_item()
        if item['identifier'] not in self._new_ids:
            self._new_ids.append(item['identifier'])
            yield item
