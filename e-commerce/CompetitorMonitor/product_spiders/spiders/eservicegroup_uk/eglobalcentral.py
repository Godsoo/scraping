# -*- coding: utf-8 -*-

"""
Notes for devs that need to fix this spider.

Eglobalcentral is a difficult site because it implements blocking of ips and we need to crawl this site 12 times per day per each eservices account.
The only way to do this effectively is:
1. To use Tor so that on each crawl we have a different ip
2. To extract prices from the product list.
   For this to be done we need to extract the skus from the previous crawl because they aren't on the list.
3. The usage of our ocr system to extract prices from images.
   Although a couple of sites(US, IT) provide prices on clear text, so we have two extraction rules for prices. One simple and one with ocr.
4. Tor is used inside the spider and not from the spider configuration. This is because for the ocr calls we don't need to use tor.

The spider works in the following way:
1. If a previous crawl exists it copies the file and loads the skus
2. Two requests to eglobal are done. One that lists in stock products and another one to list out of stock products.
   The only way to know the stock status from the list is by using this filter.
   The request set the number of products to be 200 per page.
   NEW: The stock filter does not work anymore, this has been removed
3. For each product on the page we get the price using ocr if the site has prices as images or just normal extracting if it's one of the others.
4. If the product was on the previous crawl, we load the other fields of the product from the previous crawl.
5. If the product is new, we go to the product's page and load everything from the page.

There are little new products from one crawl to another so most products will get extracted from the list.
On average, these sites have 1700 products each, leading to a small number of requests required to get all the products.

"""


import os
import csv
import json
import time
import shutil
import random
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from urllib import urlencode
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import TOR_PROXY

from product_spiders.contrib.proxyservice import ProxyServiceAPI
from product_spiders.config import (
    PROXY_SERVICE_HOST,
    PROXY_SERVICE_USER,
    PROXY_SERVICE_PSWD,
)
PROXY_SERVICE_TARGET_ID = 26

HERE = os.path.abspath(os.path.dirname(__file__))


class EGlobalCentral(BaseSpider):
    name = "eglobalcentral.co.uk"
    allowed_domains = ["eglobalcentral.co.uk", "searchanise.com", "148.251.79.44"]
    ocr_url = 'http://148.251.79.44/ocr/get_price_from_image'
    search_url = 'http://www.eglobalcentral.co.uk/product?subcats=Y&status=A&pshort=Y&pfull=Y&pname=Y&pkeywords=Y&search_performed=Y&hint_q=Search%20products&items_per_page=100'
    searchanise_url = 'http://www.searchanise.com/getwidgets?api_key={}&q=&restrictBy%5Bstatus%5D=A&restrictBy%5Bempty_categories%5D=N&restrictBy%5Busergroup_ids%5D=0%7C1&restrictBy%5Bcategory_usergroup_ids%5D=0%7C1&maxResults=100&startIndex={}&items=true&pages=true&facets=false&categories=true&suggestions=false&pagesMaxResults=3&categoriesMaxResults=3&suggestionsMaxResults=4&output=jsonp&queryBy[description]= '
    searchanise_api = '8Y3U6S6p1Y'
    use_searchanise = True
    data_file = os.path.join(HERE, 'eglobal.csv')
    products = 0
    rotate_agent = True
    use_phantomjs = False
    products_xpath = '//td[@class="product-cell"]'
    handle_httpstatus_list = [403, 502]

    def get_proxy(self):
        if self.use_phantomjs:
            return ''
        else:
            return random.choice(self.proxy_list)['url']

    def get_url(self, url):
        if self.use_phantomjs and not url.startswith('http://148.251.79.44:6543/ocr/get_page'):
            params = {'url': url, 'delay': 80, 'proxy': TOR_PROXY}
            return 'http://148.251.79.44:6543/ocr/get_page?' + urlencode(params)
        else:
            return url

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            shutil.copy('data/%s_products.csv' % self.prev_crawl_id, self.data_file)

        self.product_info = {}
        if os.path.exists(self.data_file):
            with open(self.data_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.product_info[row.get('id') or row.get('url')] = {'sku': row['sku'],
                                                                          'price': row['price']}
        if not self.use_searchanise:
            proxy_service_api = ProxyServiceAPI(host=PROXY_SERVICE_HOST, user=PROXY_SERVICE_USER,
                                                password=PROXY_SERVICE_PSWD)
            self.proxy_list = proxy_service_api.get_proxy_list(PROXY_SERVICE_TARGET_ID, log=self.log, length=100)
            yield Request(self.get_url(self.search_url),
                          callback=self.parse_category,
                          meta={'proxy': self.get_proxy(),
                                'dont_merge_cookies': True,
                                'is_search_query': True,
                                'page': 1})
        else:
            yield Request(self.searchanise_url.format(self.searchanise_api, 0), meta={'offset': 0},
                          callback=self.parse_searchanise)

    def parse_searchanise(self, response):
        res = json.loads(response.body)
        items = []
        try:
            items = res['items']
        except KeyError:
            self.log('Wrong response: {}'.format(str(res)))

            retries = response.meta.get('retries', 0)
            if retries < 5:
                time.sleep(60)
                yield Request(response.url, dont_filter=True, callback=self.parse_searchanise,
                              meta={'offset': response.meta['offset'], 'retries': retries + 1})

        for item in items:
            if not item['product_code']:
                continue
            loader = ProductLoader(item=Product(), selector=HtmlXPathSelector())
            loader.add_value('identifier', item['product_code'])
            loader.add_value('sku', item['product_code'])
            price = item['price']
            if '.' in price:
                price = price.split('.')
                price = price[0] + '.' + price[1][:2]
            loader.add_value('price', price)
            loader.add_value('name', item['title'])
            loader.add_value('url', item['link'])
            loader.add_value('stock', '1')
            yield loader.load_item()

        if items:
            meta = {'offset': response.meta['offset'] + 99}
            yield Request(self.searchanise_url.format(self.searchanise_api, meta['offset']), meta=meta,
                          callback=self.parse_searchanise)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)


        products = hxs.select(self.products_xpath)
        self.log('{} products found'.format(len(products)))
        for p in products:
            loader = ProductLoader(selector=p, item=Product())
            name = p.select('.//td[@class="product-title-wrap"]/a/text()').extract()
            if not name:
                continue
            loader.add_value('name', name)
            loader.add_value('stock', 1)
            try:
                url = p.select('.//td[@class="product-title-wrap"]/a/@href').extract()[0]
                url = urljoin_rfc(base_url, url)

                loader.add_value('url', url)
                product_id = p.select('.//input[contains(@name, "[product_id]")]/@value').extract()[0]
                price_num = p.select('.//span[@class="price-num"]/text()')
                if price_num:
                    price = ''.join(price_num.extract())
                    loader.add_value('price', price)
                    product_url = url
                    if product_id in self.product_info or product_url in self.product_info:
                        p_cache = self.product_info.get(product_id) or self.product_info.get(product_url)
                        loader.add_value('identifier', p_cache['sku'].upper())
                        loader.add_value('sku', p_cache['sku'])
                        self.products += 1
                        yield loader.load_item()
                    else:
                        yield Request(self.get_url(loader.get_output_value('url')),
                                      callback=self.parse_product, cookies={},
                                      meta={'proxy': self.get_proxy(),
                                            'loader': loader, 'product_id': product_id,
                                            'dont_merge_cookies': True})

                else:
                    price_image = p.select('.//span[@class="price"]//img/@src').extract()[0]
                    params = {'url': price_image, 'resize': 200, 'blur': 1, 'mode': '7', 'format': 'float'}
                    prev_price = self.product_info.get(product_id, {}).get('price') \
                                 or self.product_info.get(url, {}).get('price')
                    yield Request(self.ocr_url, method="POST",
                                  body=urlencode(params), meta={'loader': loader,
                                                                'product_id': product_id,
                                                                'price_image': price_image,
                                                                'prev_price': prev_price},
                                  callback=self.parse_price, dont_filter=True)
            except IndexError:
                continue

        next_category_url = hxs.select('//div[@id="pagination_contents"]//a[@name="pagination"][contains('
                                        '@class, "next")]/@href').extract()

        retries = response.meta.get('retries', 0)
        if len(next_category_url) > 0 or len(products) > 190:
            page = int(response.meta.get('page', 1)) + 1
            next_url = add_or_replace_parameter(self.search_url, 'page', str(page))
            yield Request(self.get_url(next_url), callback=self.parse_category, cookies={}, dont_filter=True,
                          meta={'proxy': self.get_proxy(),
                                'dont_merge_cookies': True,
                                'page': page})
        elif retries < 3 and (response.status != 200 or not next_category_url or not len(products)):
            page = int(response.meta.get('page', 1))
            next_url = add_or_replace_parameter(self.search_url, 'page', str(page))
            yield Request(self.get_url(next_url), callback=self.parse_category, cookies={}, dont_filter=True,
                          meta={'proxy': self.get_proxy(),
                                'dont_merge_cookies': True,
                                'page': page, 'retries': retries + 1})
        

    def parse_price(self, response):
        loader = response.meta['loader']
        res = json.loads(response.body)
        price = res['price'].split('.')
        price = price[0] + '.' + price[1][:2]

        prev_price = response.meta.get('prev_price')
        if prev_price and prev_price != price and (prev_price in price or price in prev_price):
            self.log('Possible price issue previous: {} current: {} image: {}'.format(prev_price, price,
                                                                                      response.meta['price_image']))
            if price in prev_price:
                price = prev_price

        loader.add_value('price', price)
        product_id = response.meta['product_id']
        product_url = loader.get_output_value('url')
        if product_id in self.product_info or product_url in self.product_info:
            p = self.product_info.get(product_id) or self.product_info.get(product_url)
            loader.add_value('identifier', p['sku'].upper())
            loader.add_value('sku', p['sku'])
            self.products += 1
            yield loader.load_item()
        else:
            yield Request(self.get_url(loader.get_output_value('url')), callback=self.parse_product, cookies={},
                          meta={'proxy': self.get_proxy(), 'loader': loader,
                                'product_id': product_id, 'dont_merge_cookies': True})


    def parse_product(self, response):
        retries = response.meta.get('retries', 0)
        if response.status != 200 and retries < 3:
            yield Request(response.url,
                          callback=self.parse_product, cookies={}, dont_filter=True,
                          meta={'proxy': self.get_proxy(),
                                'loader': response.meta['loader'],
                                'product_id': response.meta['product_id'],
                                'dont_merge_cookies': True, 'retries': retries + 1})

        hxs = HtmlXPathSelector(response)

        loader = response.meta['loader']

        out_stock = hxs.select('//span[contains(@id, "out_of_stock")]/text()').extract()
        if out_stock:
            loader.add_value('stock', 0)
        else:
            loader.add_value('stock', 1)
        sku = hxs.select('//span[contains(@id, "product_code")]/text()').extract()[0]
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        self.product_info[response.meta['product_id']] = {'sku': loader.get_output_value('identifier')}
        self.products += 1
        yield loader.load_item()
