import os
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product
from axemusic_item import ProductLoader

from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class AvShopSpider(BaseSpider):
    name = 'avshop.ca'
    allowed_domains = ['avshop.ca']
    #start_urls = ['http://www.avshop.ca/site_map']
    start_urls = ['http://www.avshop.ca']
    '''
    def parse(self, response):
        hxs = HtmlXPathSelector(response)    
        categories = hxs.select('//*[@id="siteMapList"]//a/@href').extract()
        for category in categories:
            yield Request(category, callback=self.parse_category)
    '''
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[contains(@id, "menu")]//a/@href').extract()
        for category in categories:
            yield Request(category, callback=self.parse_category)
   
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        sub_categories = hxs.select('//div[@id="subcategories"]//a/@href').extract()
        if sub_categories:
            for sub_category in sub_categories:
                yield Request(sub_category, callback=self.parse_category)
        else:
            yield Request(response.url, dont_filter=True, callback=self.parse_products)
    
    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        
        products = hxs.select('//div[@id="productListing"]//h5[a[contains(@class, "product-name")]]/..')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('name', './/a/text()')
            url = product.select('.//a/@href').extract()[0]
            loader.add_value('url', url)
            price = product.select('..//div[@class="product-buttons"]//span[@class="sellPrice"]/text()').extract()
            if not price:
                price = product.select('..//div[@class="product-buttons"]//div[@class="productSpecialPrice"]/span/text()').extract()
            loader.add_value('price', price[0])
            yield Request(url, callback=self.parse_product, meta={'loader':loader})#loader.load_item()
        next = hxs.select('//a[@title=" Next Page "]/@href').extract()
        if next:
            url =  urljoin_rfc(get_base_url(response), next[0])
            yield Request(url, callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = response.meta['loader']

        options = hxs.select('//div[contains(@class, "ChildListItem")]')
        
        identifier = hxs.select('//input[@name="products_id"]/@value').extract()
        if identifier:
            identifier = identifier[0]
        else:
            identifier = hxs.select('//input[@name="bundle_id"]/@value').extract()
            if identifier:
                identifier = identifier[0]
            else:
                identifier = re.search(r'popup_image/pID/(.*.?)" target', response.body)
                if identifier:
                    identifier = identifier.group(1)
                else:
                    identifier = hxs.select('//form[@name="cart_quantity"]/@action').extract()
                    if identifier:
                        identifier = identifier[0].split('?')[0].split('p-')[-1]
                    else:
                        if not options:
                            log.msg('IDENTIFIER NOT FOUND')
                            return

        loader.add_value('identifier', identifier)
        sku = ''.join(hxs.select('//span[@itemprop="identifier"]/text()').extract()).strip()
        if not sku:
            sku = ''.join(hxs.select('//div[@id="productDescription"]/text()').re('UPC: (.*)'))

        loader.add_value('sku', sku) 
        category = hxs.select('//span[@itemprop="title"]/text()').extract()[-1]
        loader.add_value('category', category)
        brand = ''.join(hxs.select('//span[@itemprop="brand"]/text()').extract())
        loader.add_value('brand', brand)
        image_url = hxs.select('//div[@id="productMainImage"]//img/@src').extract()
        if image_url:
            image_url = urljoin_rfc(get_base_url(response), image_url[0])
            loader.add_value('image_url', image_url)
 
        if options:
            product_option = loader.load_item()
            for option in options:
                product_option['identifier'] = option.select('@id').extract()[0].replace('prod_', '')
                product_option['name'] = option.select('div/span[contains(@class, "ChildListName")]/text()').extract()[0]
                price = option.select('div/span[contains(@class, "ChildListPrice")]/text()').extract()[0].replace('$', '')
                product_option['price'] = price
                yield product_option
        else:
            yield loader.load_item()
        
