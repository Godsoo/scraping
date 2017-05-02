# -*- coding: utf-8 -*-

from urlparse import urljoin, urlsplit
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import json
from scrapy.utils.url import add_or_replace_parameter
from scrapy.contrib.spidermiddleware.httperror import HttpError


class VogueWigs(BaseSpider):
    name = "voguewigs.com"
    allowed_domains = ["voguewigs.com"]
    start_urls = ["http://www.voguewigs.com/all-wigs.html",
                  'http://www.voguewigs.com/all-hairpieces.html',
                  'http://www.voguewigs.com/all-hair-extensions.html',
                  'http://www.voguewigs.com/all-costumes.html',
                  'http://www.voguewigs.com/all-accessories.html',
                  'http://www.voguewigs.com/all-sale.html']
    
    #rotate_agent = True
    #download_delay = 8
    
    def start_requests(self):
        for url in self.start_urls:
            yield Request(url, 
                          callback=self.parse_category, 
                          errback=lambda failure, retries=0,
                url=url, callback=self.parse_category: self.on_error(failure, retries, url, callback))

    def proxy_service_check_response(self, response):
        hxs = HtmlXPathSelector(response)
        return hxs.select('//div[@id="distil_ident_block"]')
    
    def on_error(self, failure, retries, url, callback):
        if isinstance(failure.value, HttpError):
            self.log('HttpError on %s. Ignoring' %url)
            return
        if retries < 50:
            self.log('Retrying %s (%s)' %(url, failure.value))
            yield Request(url, 
                          callback=callback,
                          meta={'retries': retries+1},
                          errback=lambda failure, retries=retries, 
                          url=url, callback=callback: self.on_error(failure, retries, url, callback),
                          dont_filter=True)
        else:
            self.log('Gave up retrying %s (%s)' %(url, failure))
            
    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        if hxs.select('//div[@id="distil_ident_block"]'):
            retries = response.meta.get('retries', 0)
            if retries < 50:
                self.log('Retrying %s (antibot protection)' %response.url)
                yield response.request.replace(meta={'retries':retries+1}, dont_filter=True)
            else:
                self.log('Gave up retrying %s (antibot protection)' %response.url)
            return
                
        category_urls = hxs.select('//div[@id="header-nav"]//a/@href').extract()
        for url in category_urls:
            link = urljoin(base_url, url)
            yield Request(link, callback=self.parse_category, errback=lambda failure, retries=0,
                url=link, callback=self.parse_category: self.on_error(failure, retries, url, callback))

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        if hxs.select('//div[@id="distil_ident_block"]'):
            retries = response.meta.get('retries', 0)
            if retries < 50:
                self.log('Retrying %s (antibot protection)' %response.url)
                yield response.request.replace(meta={'retries':retries+1}, dont_filter=True)
            else:
                self.log('Gave up retrying %s (antibot protection)' %response.url)
            return
                
        product_urls = hxs.select('//h3/a/@href').extract()
        product_urls += hxs.select('//h2/a/@href').extract()
        product_urls += hxs.select('//div[contains(@id, "productData")]//a/@href').extract()
        for url in product_urls:
            link = urljoin(base_url, url)
            yield Request(link, callback=self.parse_product, errback=lambda failure, retries=0,
                url=link, callback=self.parse_product: self.on_error(failure, retries, url, callback))

        product_urls = hxs.select('//h1/a/@href').extract()
        for url in product_urls:
            link = urljoin(base_url, url)
            yield Request(link, callback=self.parse_product, errback=lambda failure, retries=0,
                url=link, callback=self.parse_product: self.on_error(failure, retries, url, callback))

        next_page_url = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next_page_url:
            yield Request(next_page_url[0], callback=self.parse_category)
            for i in xrange(1, 12):
                url = add_or_replace_parameter(response.url, 's', str(i))
                yield Request(url, callback=self.parse_category, errback=lambda failure, retries=0,
                url=url, callback=self.parse_category: self.on_error(failure, retries, url, callback))
                
        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            link = urljoin(base_url, url)
            yield Request(link, callback=self.parse_category, errback=lambda failure, retries=0,
                url=link, callback=self.parse_category: self.on_error(failure, retries, url, callback))

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        
        for product in self.parse_category(response):
            yield product

        if hxs.select('//div[@id="distil_ident_block"]'):
            retries = response.meta.get('retries', 0)
            if retries < 50:
                self.log('Retrying %s (antibot protection)' %response.url)
                yield response.request.replace(meta={'retries':retries+1}, dont_filter=True)
            else:
                self.log('Gave up retrying %s (antibot protection)' %response.url)
            return
                
        loader = ProductLoader(selector=hxs, item=Product())

        products = hxs.select('//div[@class="u-cms-frame"]//h1/a/@href').extract()
        for product in products:
            url = urljoin(base_url, product)
            yield Request(url, callback=self.parse_product, errback=lambda failure, retries=0,
                url=url, callback=self.parse_product: self.on_error(failure, retries, url, callback))

        product_name = hxs.select('//*[@id="product_addtocart_form"]//div[@class="product-name"]/h1/text()').extract()
        if not product_name:
            self.log('Warning: no product name: {}'.format(response.url))
            return
        else:
            product_name = product_name[0]
        brand = hxs.select('//*[@id="product_addtocart_form"]//span[@class="product-phrase"]/text()').extract()
        if not brand:
            brand = hxs.select('//div[@class="product-attributes"]//span[@class="product-phrase"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_xpath('price', '//*[@id="product_addtocart_form"]//span[@class="price"]/text()')
        price = hxs.select('//*[@id="product_addtocart_form"]//span[@class="price"]/text()').extract()
        if price:
            price = extract_price(price[0])
        else:
            price = extract_price('0')
        image_url = hxs.select('//*[@id="image-main"]/@src').extract()
        sku = hxs.select('//div[@class="label-container"]/label[text()="Sku:"]/../../div/span/text()').extract()
        sku = sku[0].strip() if sku else ''
        product_identifier = urlsplit(response.url).path
        product_identifier = product_identifier.strip('/')
        product_identifier = product_identifier.split('.')[0]

        products = {}
        has_options = False
        options_config = re.search(r'var spConfig *= *new Product.Config\((.*)\)', response.body)
        colors_data = re.search(r'<script.*>ColorOverlay\.setData\((.*?)\);', response.body)

        if colors_data:
            colors_data = json.loads(colors_data.groups()[0])
            if isinstance(colors_data, dict):
                if colors_data.keys()[0] != u'':
                    has_options = True
                    for color in colors_data.itervalues():
                        products[color['color_label']] = color['color_name']

        if options_config:
            product_data = json.loads(options_config.groups()[0])
            if product_data['attributes']:
                has_options = True
                for attr in product_data['attributes'].itervalues():
                    for option in attr['options']:
                        products[option['label']] = option['label']

        if has_options:
            for identifier, option_name in products.iteritems():
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', product_identifier + '_' + identifier)
                product_loader.add_value('name', product_name + ' ' + option_name)
                if image_url:
                    product_loader.add_value('image_url', urljoin(base_url, image_url[0]))
                if price < 50.0:
                    product_loader.add_value('shipping_cost', 7.95)
                else:
                    product_loader.add_value('shipping_cost', 0)
                product_loader.add_value('price', price)
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('sku', sku)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin(base_url, image_url[0]))
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            if price < 50.0:
                product_loader.add_value('shipping_cost', 7.95)
            else:
                product_loader.add_value('shipping_cost', 0)
            product_loader.add_value('sku', sku)
            product = product_loader.load_item()
            yield product
