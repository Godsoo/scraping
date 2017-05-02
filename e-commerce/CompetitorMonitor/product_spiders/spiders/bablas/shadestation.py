'''
One or number of new products on the site with price 230 GBP raise site error while trying to load product list page. So we need to hardcode minimum and maximum price to parse the maximum number of products
'''

import os
import pandas as pd
import json
import random
import time
from itertools import cycle
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from product_spiders.items import Product
from bablas_item import ProductLoader
from product_spiders.config import DATA_DIR
from product_spiders.utils import extract_price
from product_spiders.contrib.proxyservice import ProxyServiceAPI
from config import PROXY_SERVICE_HOST, PROXY_SERVICE_USER, PROXY_SERVICE_PSWD
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher


class ShadeStationSpider(BaseSpider):
    name = 'shadestation.co.uk'
    allowed_domains = ['shadestation.co.uk']
    start_urls = ['https://www.shadestation.co.uk/']

    #rotate_agent = True

    ajax_products_url = 'http://www.shadestation.co.uk/return_products.php'
    product_page_identifier_xpath = u'//div[label[text()="Shade Station code"]]/span/text()'

    proxy_service_target_id = 166

    def __init__(self, *args, **kwargs):
        super(ShadeStationSpider, self).__init__(*args, **kwargs)

        self.products_cache_filename = ''
        self.products_cache = None
        self.new_products_urls = set()
        self.search_finished = False
        self.spider_finished = False
        self.maxpages = 10000

        self.current_cookie = 0

        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self):
        if self.search_finished and (not self.spider_finished):
            request = Request('http://www.shadestation.co.uk',
                              dont_filter=True,
                              callback=self.parse_new_products)
            self._crawler.engine.crawl(request, self)

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            self.products_cache_filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            self.products_cache = pd.read_csv(self.products_cache_filename, dtype=pd.np.str)
            self.products_cache = self.products_cache.where(pd.notnull(self.products_cache), None)
            self.products_cache['viewed'] = False

        for url in self.start_urls:
            yield Request(url, meta={'cookiejar': self.current_cookie})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        page_no = response.meta.get('_page_', 1)

        headers = {'X-Request': 'JSON',
                   'x-requested-with': 'XMLHttpRequest',
                   'Accept': 'application/json'}
        all_params = ({'limit': '28',
                  'orderby': 'high-low',
                  'pageno': str(page_no)},
                {'limit': '28',
                  'menswomens': 'true',
                  'orderby': 'high-low',
                  'pageno': str(page_no),
                  'minprice[1]': '231.1'},
                {'limit': '28',
                  'menswomens': 'true',
                  'orderby': 'high-low',
                  'pageno': str(page_no),
                  'maxprice[0]': '230.9'})
            
        for params in all_params[:1]:
            req = FormRequest(self.ajax_products_url,
                          formdata=params,
                          headers=headers,
                          dont_filter=True,
                          meta={'_params_': params,
                                '_headers_': headers,
                                '_page_': page_no,
                                'cookiejar': self.current_cookie},
                          callback=self.parse_result)
        
            yield req

    def parse_result(self, response):
        base_url = get_base_url(response)
        
        try:
            data = json.loads(response.body)
        except ValueError:
            self.logger.error('No json data with params %s and page %s' %(response.meta['_params_'], response.meta['_page_']))
            data = {'data': []}
        else:
            if self.maxpages == 10000:
                self.maxpages = data['maxpages']
            
        if int(response.meta['_page_']) <= self.maxpages:
            params = response.meta['_params_'].copy()
            params['pageno'] = str(int(response.meta['_page_']) + 1)
            yield FormRequest(self.ajax_products_url,
                              formdata=params,
                              headers=response.meta['_headers_'],
                              dont_filter=True,
                              meta={'_params_': params,
                                    '_headers_': response.meta['_headers_'],
                                    '_page_': params['pageno'],
                                    'cookiejar': self.current_cookie},
                              callback=self.parse_result)
        else:
            self.search_finished = True

        products = data['data']
        for product in products:
            identifier = product['prodid']
            price = product['ourprice']
            in_stock = bool(product['stockstatus'] == 'In Stock')
            product_url = urljoin_rfc(base_url, product['url'])
            product_url = add_or_replace_parameter(product_url, 'currency', 'GBP')

            if self.products_cache is not None:
                cached_item = self.products_cache[self.products_cache['identifier'] == identifier]
                if not cached_item.empty:
                    cached_item_dict = dict(cached_item.iloc[0])
                    del cached_item_dict['viewed']
                    cached_product = Product(cached_item_dict)
                    cached_product['price'] = Decimal(extract_price(price))
                    del cached_product['dealer']
                    if cached_product['name'] is None:
                        del cached_product['name']
                    if cached_product['category'] is None:
                        del cached_product['category']
                    if cached_product['shipping_cost']:
                        cached_product['shipping_cost'] = Decimal(cached_product['shipping_cost'])
                    else:
                        del cached_product['shipping_cost']
                    if not in_stock:
                        cached_product['stock'] = 0
                    else:
                        del cached_product['stock']
                    self.products_cache['viewed'].loc[cached_item.index] = True
                    yield cached_product
                else:
                    self.new_products_urls.add(urljoin_rfc(base_url, product_url))
            else:
                self.new_products_urls.add(urljoin_rfc(base_url, product_url))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        identifier = hxs.select(self.product_page_identifier_xpath).extract()
        if identifier:
            identifier = identifier[0].strip()
        else:
            retry_no = int(response.meta.get('retry_no', 0))
            if retry_no < 20:
                retry_no += 1
                yield Request(response.url,
                              meta={'dont_merge_cookies': True,
                                    'retry_no': retry_no},
                              dont_filter= True,
                              callback=self.parse_product)
            else:
                self.log('WARNING: possible blocking in => %s' % response.url)

            return

        sku = hxs.select(u'//span[@itemprop="productID"]/text()').extract()
        sku = sku[0] if sku else ''

        category = hxs.select(u'//div[@itemprop="breadcrumb"]/a/text()').extract()
        category = category[-1].strip() if category else ''
        loader.add_value('identifier', identifier)
        loader.add_xpath('name', u'//h1[@itemprop="name"]/text()')
        loader.add_value('brand', category)
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        price = hxs.select(u'//div[@itemprop="price"]/text()').re('Our Price (.*)')
        if not price:
            price = hxs.select(u'//div[@itemprop="price"]/text()').extract()
        price = price[0] if price else '0.00'
        loader.add_value('price', price)
        image = hxs.select(u'//div[@id="product_image_crop"]/div/@imageurl').extract()
        image = image[0] if image else ''
        image = urljoin_rfc(base_url, image)
        loader.add_value('image_url', image)

        out_of_stock = hxs.select(u'//div[@itemprop="availability"]/text()').re(r'(?i)out of stock')
        if out_of_stock:
            stock = 0
        else:
            stock_availability = hxs.select(u'//div[@class="stockstatus"]/div[@class="actualstatus" and child::*]/text()').extract()
            if not stock_availability:
                stock_availability = hxs.select(u'//div[@class="stockstatus"]/div[@class="sitestatus"]/div[@class="actualstatus" and child::*]/text()').extract()
            if stock_availability:
                stock = hxs.select(u'//div[@class="stockstatus"]/div[@class="furtherdetails"]/text()').re(u'[\d]+')
                if not stock:
                    stock = hxs.select(u'//div[@class="stockstatus"]/div[@class="sitestatus"]/div[@class="furtherdetails"]/text()').re(u'[\d]+')
                stock = int(stock[0])
            else:
                stock = None
        loader.add_value('stock', stock)
        yield loader.load_item()

    def parse_new_products(self, response):
        self.spider_finished = True
        cookie_no = 0
        self.logger.debug('%d product urls collected' %len(self.new_products_urls))
        for product_url in self.new_products_urls:
            cookie_no += 1
            yield Request(product_url,
                          callback=self.parse_product,
                          meta={'cookiejar': cookie_no})


