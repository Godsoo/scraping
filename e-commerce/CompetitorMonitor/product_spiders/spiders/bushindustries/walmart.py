'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5547
'''

import os
import csv
from product_spiders.config import DATA_DIR
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from scrapy.utils.url import add_or_replace_parameter, url_query_cleaner, url_query_parameter

from product_spiders.items import (
    Product,
    ProductLoaderWithoutSpaces as ProductLoader
)

import json
import re
from urlparse import urljoin
from product_spiders.utils import extract_price
from urllib import quote


class WalmartSpider(CrawlSpider):
    name = 'bushindustries-walmart.com'
    allowed_domains = ['walmart.com']
    start_urls = ('https://www.walmart.com/cp/furniture/103150',)
    
    product_urls = ('https://www.walmart.com/ip/Bush-Industries-Universal-72-Bookcase/16402615',
                    'https://www.walmart.com/ip/Bush-Industries-Cabot-L-Shape-Desk-with-Hutch/48777898',
                    'https://www.walmart.com/ip/Bush-Industries-Cabot-Corner-Desk-with-Hutch/48777912',
                    'https://www.walmart.com/ip/Bush-Fairview-Collection-L-Shaped-Desk-Antique-Black-and-Cherry/29376771',
                    'https://www.walmart.com/ip/Bush-30-in.-Lateral-File-Harvest-Cherry/26126429',
                    'https://www.walmart.com/ip/Bush-Furniture-Cabot-Collection-60-Overhead-Hutch-Harvest-Cherry/35284618',
                    'https://www.walmart.com/ip/Bush-Furniture-Cabot-6-Cube-Bookcase-Harvest-Cherry/26126500')

    deduplicate_identifiers = True
    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:49.0) Gecko/20100101 Firefox/49.0'
    custom_settings = {'COOKIES_ENABLED': False,
                       'RETRY_HTTP_CODES': [520, 500, 501, 502, 503, 504, 400, 401, 408, 403, 456, 429]}
    
    categories = LinkExtractor(restrict_css=('div.PopularCategories',
                                             'div.shelf-sidebar div.SideBarMenuModule:first-child',
                                             'div.merchant-module',
                                             'div.paginator ul.paginator-list'))
    pages = LinkExtractor(restrict_css='div.paginator ul.paginator-list')
    products = LinkExtractor(restrict_xpaths='//div[@id="tile-container"]',
                             restrict_css=('a.js-product-title',
                                           'a.search-result-product-title'))
    
    rules = (Rule(products, callback='parse_product'),
             Rule(categories, callback='parse_category', follow=True))

    def start_requests(self):
        for url in self.product_urls:
            yield Request(url, self.parse_product)
        return
        
        for request in super(WalmartSpider, self).start_requests():
            yield request
            
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            
            with open(filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield Request(row['url'], self.parse_product)
                                  
    def parse_category(self, response):
        products = self.products.extract_links(response)
        if not products:
            retries = response.meta.get('retries', 0)
            if retries < 3:
                yield Request(response.url,
                              self.parse_category,
                              meta={'retries': retries+1},
                              dont_filter=True)
        for product in products:
            yield Request(product.url,
                          self.parse_product)

    def parse_product(self, response):
        data = response.xpath('//script/text()[contains(., "product/data")]').extract_first()
        rdata = response.xpath('//script/text()[contains(., "window.__WML_REDUX_INITIAL_STATE__")]').extract_first()
        if not data:
            if rdata:
                for product in self.parse_product_rdata(response):
                    yield product
            else:
                retries = response.meta.get('retries', 0)
                if retries < 20:
                    self.logger.warning('No product data on %s. Retrying.' %response.url)
                    yield Request(response.url,
                                self.parse_product,
                                meta={'retries': retries+1},
                                dont_filter=True)
                else:
                    self.logger.warning('No product data found on %s. Gave up retrying' %response.url)
            return
        
        data = json.loads(re.search('product/data",[ \n]*({.+})', data).group(1))

        loader = ProductLoader(item=Product(), response=response)

        product_id = response.xpath('//form[@name="SelectProductForm"]/input[@name="product_id"]/@value').extract()
        if product_id:
            identifier = product_id[0]
        else:
            identifier = url_query_cleaner(response.url).split('/')[-1]
        identifier = identifier.split('?')[0]

        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        name = filter(lambda n: n, map(unicode.strip, response.xpath('//h1[@itemprop="name"]//text()').extract()))
        if not name:
            name = filter(lambda n: n, map(unicode.strip, response.xpath('//h1[contains(@class,"product-name")]//text()').extract()))
        if name:
            loader.add_value('name', name[0].strip())
        #loader.add_xpath('name', '//option[@selected and not(@disabled)]/text()')

        loader.add_css('brand', 'a.product-brand span::text')

        categories = response.xpath('//div[@itemprop="breadcrumb"]//span[@itemprop="title"]/text()').extract()
        if not categories:
            categories = response.xpath('//div[@itemprop="breadcrumb"]//span[@itemprop="name"]/text()').extract()
        if categories:
            if 'Home' in categories:
                categories.remove('Home')
            loader.add_value('category', categories)
        elif 'category' in response.meta:
            loader.add_value('category', response.meta['category'])

        loader.add_value('url', response.url)
        
        price = response.xpath('//@data-product-price').extract_first()
        if price:
            price = [price] if price else None
        if not price:
            price = response.xpath('//div[@id="WM_PRICE"]//*[contains(@class,"camelPrice")]/span/text()').extract()
        if not price:
            price = response.xpath('//div[@class="onlinePriceMP"]//*[contains(@class,"camelPrice")]/span/text()').extract()
        if not price:
            price = response.xpath('//div[@itemprop="offers"]/div[contains(@class, "product-price")]//*[@itemprop="price"][1]//text()').extract()
        if not price:
            price = response.xpath('//div[@class="col5"]//div[contains(@class,"product-buying-table-row")][1]//div[contains(@class,"price-display")][1]//text()').extract()
        if not price:
            price = response.xpath('//*[@itemprop="price"]//text()').extract()
        
        price = ''.join(price).strip() if price else 0

        loader.add_value('price', price)

        stock = response.xpath('//meta[@itemprop="availability"]/@content').extract_first()
        if not stock or stock != 'InStock':
            loader.add_value('stock', 0)

        image = response.xpath('//div[@class="LargeItemPhoto215"]//img/@src').extract()
        if not image:
            image = response.xpath('//div[contains(@class,"product-images")][1]//img/@src').extract()
        if image:
            loader.add_value('image_url', image[0])
        
        try:
            loader.add_value('shipping_cost', data['buyingOptions']['shippingPrice']['displayPrice'])
        except KeyError:
            loader.add_css('shipping_cost', 'h2.js-shipping-primary-msg::text')
        
        if not data or not data.get('variantInformation'):
            yield loader.load_item()
            return
        
        if url_query_parameter(response.url, 'selected'):
            if response.css('div.product-buying-table').xpath('.//div[contains(., "Information unavailable")]') or price == 0:
                retries = response.meta.get('retries', 0)
                if retries < 9:
                    yield Request(response.url, 
                                  self.parse_product, 
                                  meta={'retries': retries+1},
                                  dont_filter=True)
                return
            for option in data['variantInformation']['variantTypes']:
                try:
                    loader.add_value('name', option['selectedValue'])
                except KeyError:
                    pass
            yield loader.load_item()
            return
        
        for variant in data['variantInformation']['variantProducts']:
            try:
                option_id = variant['buyingOptions']['usItemId']
            except KeyError:
                continue
            url = '/'.join(response.url.split('/')[:-1])
            url += '/%s' % option_id
            yield Request(add_or_replace_parameter(url, 'selected', 'True'),
                          self.parse_product)

    def parse_product_rdata(self, response):
        data = response.xpath('//script/text()[contains(., "window.__WML_REDUX_INITIAL_STATE__")]').extract_first()
        data = json.loads(re.search("window.__WML_REDUX_INITIAL_STATE__ = ({.+})", data).group(1))
        for product in data['product']['products'].itervalues():
            if not url_query_parameter(response.url, 'selected') or not product.get('productAttributes'):
                url = '/'.join(response.url.split('/')[:-1])
                url += '/%s' % product['usItemId']
                yield Request(add_or_replace_parameter(url, 'selected', 'True'),
                            self.parse_product)
                continue
            attrs = product['productAttributes']
            offer = product['offers'][0]
            image = product['images'][0]
            loader = ProductLoader(Product(), response=response)
            loader.add_value('identifier', product['usItemId'])
            loader.add_value('sku', product['usItemId'])
            loader.add_value('name', attrs['productName'])
            if product.get('variants'):
                loader.add_value('name', product['variants'].values())
            loader.add_value('price', data['product']['offers'][offer]['pricesInfo']['priceMap']['CURRENT']['price'])
            loader.add_value('url', response.url)
            loader.add_value('category', attrs['productCategory']['categoryPath'].split('/'))
            loader.add_value('brand', attrs['brand'])
            loader.add_value('image_url', data['product']['images'][image]['assetSizeUrls']['main'])
            loader.add_value('shipping_cost', data['product']['offers'][offer].get('shippingPrice'))
            if data['product']['offers'][offer]['productAvailability']['availabilityStatus'] != 'IN_STOCK':
                loader.add_value('stock', 0)
            yield loader.load_item()
        
    def parse_option(self, response):
        data = json.loads(response.body)
        loader = response.meta['loader']
        loader.replace_value('price', data['product']['buyingOptions']['price']['displayPrice'])
        loader.replace_value('shipping_cost', data['product']['buyingOptions']['shippingPrice']['displayPrice'])
        loader.replace_value('image_url', response.urljoin(data['product']['imageAssets'][0]['versions']['hero']))
        
        