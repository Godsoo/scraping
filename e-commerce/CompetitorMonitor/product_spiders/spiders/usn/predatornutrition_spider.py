import os
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from urlparse import urljoin
from w3lib.url import add_or_replace_parameter

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))

class PredatorNutritionSpider(BaseSpider):
    name = 'usn-predatornutrition.com'
    allowed_domains = ['predatornutrition.com']
    start_urls = ['http://www.predatornutrition.com']

    rotate_agent = True

    def start_requests(self):
        brands = {'USN': ['http://www.predatornutrition.com/shop-by-brand/usn'],
                  'Optimum Nutrition': ['http://www.predatornutrition.com/shop-by-brand/optimum-nutrition'],
                  'BSN': ['http://www.predatornutrition.com/shop-by-brand/bsn'],
                  'PhD': ['http://www.predatornutrition.com/shop-by-brand/phd-nutrition'],
                  'Maxi Nutrition': ['http://www.predatornutrition.com/shop-by-brand/maxinutrition'],
                  'Reflex': ['http://www.predatornutrition.com/shop-by-brand/reflex'],
                  'Mutant': ['http://www.predatornutrition.com/shop-by-brand/mutant'],
                  'Cellucor': ['http://www.predatornutrition.com/shop-by-brand/cellucor'],
                  'Sci-MX': ['http://www.predatornutrition.com/shop-by-brand/sci-mx']}

        cookies = {'GlobalE_Data': {'countryISO': 'GB', 'cultureCode': 'en', 'currencyCode': 'GBP'}}

        for brand_name, urls in brands.iteritems():
            for url in urls:
                link = add_or_replace_parameter(url, 'viewAll', 'true')
                yield Request(link, meta={'brand': brand_name}, cookies=cookies)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = response.xpath('//div[@class="product-name"]/a/@href').extract()
        for product in products:
            yield Request(urljoin(base_url, product), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        html = response.body.replace('&amp;', '&')
        hxs = HtmlXPathSelector(text=html)

        identifier = hxs.select('//input[@id="pid"]/@value').extract()
        if not identifier:
            self.log('PRODUCT WITHOUT IDENTIFIER: ' + response.url)
            return

        loader = ProductLoader(item=Product(), response=response)
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        if name.startswith(':'):
            name = name[1:]
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta.get('brand', ''))

        categories = hxs.select('//a[@class="breadcrumb-element"]/@href/../text()').extract()
        categories.remove('Home')
        loader.add_value('category', categories)

        loader.add_value('sku', identifier[0])
        loader.add_value('identifier', identifier[0])
        loader.add_xpath('image_url', '//div[@class="product-primary-image"]/a/@href')

        loader.add_xpath('price', '//div[@id="product-content"]//span[@class="price-sales"]/meta/@content')

        out_of_stock = hxs.select('//p[contains(@class, "not-available")]')
        if out_of_stock:
            loader.add_value('stock', 0)

        if loader.get_output_value('price') <= 59.99:
            loader.add_value('shipping_cost', 1.99)

        item = loader.load_item()

        if item.get('price', None) and item['price'] <= 59.99:
            item['shipping_cost'] = 1.99

        options = hxs.select('//select')
        for option in options:
            for variant in option.select('./option'):
                if variant.select('./@selected'):
                    var_name = variant.select('./text()').extract()[0].strip().replace('&amp;', '&')
                    item['name'] += ' ' + var_name
                else:
                    option_url = variant.select('./@value').extract()[0].replace('&amp;', '&') + '&Quantity=1&uuid=&format=ajax'
                    meta = response.meta
                    meta['item'] = deepcopy(item)
                    meta['base_name'] = name
                    yield Request(option_url, callback=self.parse_option, meta=meta)

        if item.get('price', None):
            yield item

    def parse_option(self, response):
        item = response.meta['item']

        identifier = response.xpath('//input[@id="pid"]/@value').extract()
        item['identifier'] = identifier[0]
        item['sku'] = identifier[0]
        item['name'] = response.meta['base_name']

        price = response.xpath('//div[@class="product-price"]/span[contains(@class, "price-sales")]/meta/@content').extract()
        if not price:
            price = response.xpath('//div[@class="product-price"]/span[contains(@class, "price-sales")]/span/text()').extract()
        
        item['price'] = extract_price(price[0]) if price else 0

        stock = response.xpath('//p[@class="in-stock-msg"]')
        if not stock:
            item['stock'] = 0

        if item['price'] <= 59.99:
            item['shipping_cost'] = 1.99

        item['url'] = response.url.replace('&Quantity=1&uuid=&format=ajax', '')
  
        options = response.xpath('//select')
        for option in options:
            for variant in option.select('./option'):
                if variant.xpath('./@selected'):
                    var_name = variant.xpath('./text()').extract()[0].strip().replace('&amp;', '&')
                    item['name'] += ' ' + var_name
                else:
                    option_url = variant.xpath('./@value').extract()[0].replace('&amp;', '&') + '&Quantity=1&uuid=&format=ajax'
                    meta = response.meta
                    yield Request(option_url, callback=self.parse_option, meta=meta)

        if item.get('price', None):
            yield item
