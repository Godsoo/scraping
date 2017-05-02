'''
The site uses DistilNetworks antibot system
We need to find real IP for this site
'''

import os
import json
import csv
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.config import DATA_DIR
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

from fragrance_direct_items import FragranceDirectMeta


class FeeluniqueSpider(BaseSpider):
    name = 'feelunique'
    allowed_domains = ['feelunique.com']
    start_urls = [
        'http://www.feelunique.com/',
    ]
    
    handle_httpstatus_list = [405]
    rotate_agent = True

    def proxy_service_check_response(self, response):
        return response.status == 405
    
    def __init__(self, *args, **kwargs):
        super(FeeluniqueSpider, self).__init__(*args, **kwargs)

        self.old_crawl_filename = ''
        self.old_urls = []

        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        while self.old_urls:
            url = self.old_urls.pop()
            request = Request(url, callback=self.parse_product)
            self._crawler.engine.crawl(request, self)

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            self.old_crawl_filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            with open(self.old_crawl_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['url'] not in self.old_urls:
                        self.old_urls.append(row['url'])

        yield Request('http://www.feelunique.com/',
                      cookies={'feeluniqueCurr': 'GBP',
                               'optin_location': 'UK'})

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//ul[contains(@class, "subnav")]/li/a/@href').extract()
        for category in categories:
            yield Request(
                urljoin_rfc(base_url, category),
                callback=self.parse_category,
            )

    def parse_category(self, response):
        if response.status == 405:
            url = response.meta['redirect_urls'][0]
            retries = response.meta.get('retries', 0)
            if retries >= 9:
                self.logger.error('Gave up retrying avoid antibot captcha for %s' %url)
                return
            self.logger.debug('DistilNetworks antibot captcha. Retrying %s' %url)
            yield response.request.replace(dont_filter=True,
                                           url=url,
                                           meta={'retries': retries+1,
                                                 'dont_merge_cookies': True})
            return
        
        base_url = get_base_url(response)

        subcats = response.xpath('//div[contains(@class, "content") and contains(@class, "nav")]//a/@href').extract()
        for url in subcats:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

        # products
        for product_url in response.xpath("//a[contains(@class, 'Product-link')]/@href").extract():
            yield Request(
                urljoin_rfc(base_url, product_url),
                callback=self.parse_product,
                meta={'cookiejar': product_url}
            )

        # next page
        next_page_url_list = response.xpath("//a[@class='forward']//@href").extract()
        if next_page_url_list:
            self.log("next page url: {}".format(next_page_url_list[0]))
            yield Request(
                urljoin_rfc(base_url, next_page_url_list[0]),
                callback=self.parse_category,
            )

    def parse_product(self, response):
        if response.status == 405:
            url = response.meta['redirect_urls'][0]
            retries = response.meta.get('retries', 0)
            if retries >= 9:
                self.logger.error('Gave up retrying avoid antibot captcha for %s' %url)
                return
            self.logger.debug('DistilNetworks antibot captcha. Retrying %s' %url)
            yield response.request.replace(dont_filter=True,
                                           url=url,
                                           meta={'retries': retries+1,
                                                 'dont_merge_cookies': True})
            return
        
        if response.url in self.old_urls:
            self.old_urls.remove(response.url)

        options_data = response.xpath("//div[@class='v2-product-subproducts']//@data").extract()
        if options_data:
            options_data = json.loads(options_data[0])

            product_name = options_data['name']
            if not options_data.get('sku', 0):
                pass
            else:

                if options_data['sub_products']:

                    for sub_option in options_data:
                        loader = ProductLoader(item=Product(), response=response)
                        price = extract_price(sub_option['prices']['price']['amount'])

                        loader.add_value('url', response.url)

                        option_name = sub_option['option1']
                        loader.add_value('name', "{product} {option}".format(
                            product=product_name,
                            option=option_name
                        ))
                        loader.add_value('stock', sub_option['stock']['is_in_stock'])

                        loader.add_xpath('category', "//div[@id='breadcrumb']//li[position() > 1 and position() < last()]//text()")
                        loader.add_xpath('brand', "//div[@class='v2-gallery-block']//img/@alt")

                        if price < 10:
                            shipping_cost = extract_price('2.95')
                        else:
                            shipping_cost = 0

                        # Add shipping cost to product price
                        loader.add_value('shipping_cost', shipping_cost)
                        loader.add_value('price', price + shipping_cost)

                        loader.add_value('sku', sub_option['sku'])
                        loader.add_value('identifier', sub_option['sku'])

                        loader.add_xpath('image_url', sub_option['main_image']['large_path'])

                        product = loader.load_item()

                        promotion = response.xpath("//div[@id='product-offer-tab']//h3//text()").extract()
                        metadata = FragranceDirectMeta()
                        if promotion:
                            metadata['promotion'] = promotion[0]
                        if product.get('price'):
                            metadata['price_exc_vat'] = Decimal(product['price']) / Decimal('1.2')
                        product['metadata'] = metadata
                        yield product
                else:
                    loader = ProductLoader(item=Product(), response=response)
                    price = extract_price(options_data['prices']['price']['amount'])

                    loader.add_value('price', price)
                    loader.add_value('url', response.url)

                    loader.add_value('name', product_name)
                    loader.add_value('stock', options_data['stock']['is_in_stock'])

                    loader.add_xpath('category', "//div[@id='breadcrumb']//li[position() > 1 and position() < last()]//text()")
                    loader.add_xpath('brand', "//div[@class='v2-gallery-block']//img/@alt")

                    if price < 10:
                        shipping_cost = extract_price('2.95')
                    else:
                        shipping_cost = 0

                    # Add shipping cost to product price
                    loader.add_value('shipping_cost', shipping_cost)
                    loader.add_value('price', price + shipping_cost)

                    loader.add_value('sku', options_data['sku'])
                    loader.add_value('identifier', options_data['sku'])

                    loader.add_value('image_url', options_data['main_image']['large_path'])

                    product = loader.load_item()

                    promotion = response.xpath("//div[@id='product-offer-tab']//h3//text()").extract()
                    metadata = FragranceDirectMeta()
                    if promotion:
                        metadata['promotion'] = promotion[0]
                    if product.get('price'):
                        metadata['price_exc_vat'] = Decimal(product['price']) / Decimal('1.2')
                    product['metadata'] = metadata
                    yield product

        else:
            product_name = response.xpath("//h1[@class='fn']//text()").extract()[0]
            options = response.xpath("//div[contains(@class, 'sub-products')]/div")
            sku = ''.join(response.xpath("//form[@name='notifications']//input[@name='p']/@value").extract())
            if options:
                for sub_option_2 in options:
                    sku_option = ''.join(sub_option_2.xpath("./label/@data-sub-sku").extract())

                    loader = ProductLoader(item=Product(), response=response)
                    price = extract_price(sub_option_2.xpath("./label/@data-subprice").extract()[0])
                    if not price:
                        price = extract_price(''.join(response.xpath('//p[@class="price-info"]//span[@class="Price"]/text()').extract()).strip())

                    loader.add_value('price', price)
                    loader.add_value('url', response.url)

                    option_name = sub_option_2.xpath("./label/@data-option").extract()[0]
                    loader.add_value('name', u"{product} {option}".format(
                        product=product_name,
                        option=option_name
                    ))

                    stock = ''.join(sub_option_2.xpath("./label/@data-stock").extract()).strip().lower()
                    if stock in ['limited', 'in stock']:
                        stock = '1'
                    else:
                        stock = '0'
                    loader.add_value('stock', stock)

                    loader.add_xpath('category', "//div[@id='breadcrumb']//li[position() > 1 and position() < last()]//text()")
                    loader.add_xpath('brand', "//a[@class='product-brand']//img/@alt")

                    if price < 10:
                        shipping_cost = extract_price('2.95')
                    else:
                        shipping_cost = 0

                    # Add shipping cost to product price
                    loader.add_value('shipping_cost', shipping_cost)
                    loader.add_value('price', price + shipping_cost)

                    loader.add_value('sku', sku_option)
                    loader.add_value('identifier', '{}_{}'.format(sku, sku_option))

                    img = ''.join(sub_option_2.xpath("./data-image-large").extract())
                    if not img:
                        img = ''.join(response.xpath("//img/@data-original-large").extract())
                    loader.add_value('image_url', 'http:' + img)

                    product = loader.load_item()

                    promotion = response.xpath("//div[@id='product-offer-tab']//h3//text()").extract()
                    metadata = FragranceDirectMeta()
                    if promotion:
                        metadata['promotion'] = promotion[0]
                    if product.get('price'):
                        metadata['price_exc_vat'] = Decimal(product['price']) / Decimal('1.2')
                    product['metadata'] = metadata
                    yield product
                return

            options = response.xpath('//option[@data-name]')
            if options:
                for opt in options:
                    loader = ProductLoader(item=Product(), response=response)
                    product_image_json = opt.xpath('@data-image').extract()
                    if product_image_json:
                        product_image_data = json.loads(product_image_json[0])
                        loader.add_value('image_url', product_image_data['default'])

                    product_stock = opt.xpath('@data-stock').extract()[0]
                    if product_stock == 'Out of Stock':
                        loader.add_value('stock', 0)

                    option_name = opt.xpath('@data-name').extract()[0]
                    loader.add_value('name', product_name + ' ' + option_name)

                    price_data = json.loads(opt.xpath('@data-price').extract()[0])
                    loader.add_value('price', price_data['price'])

                    option_sku = opt.xpath('@value').extract()[0]
                    loader.add_value('sku', option_sku)
                    loader.add_value('identifier', sku + '_' + option_sku)

                    loader.add_xpath('category', "//div[@id='breadcrumb']//li[position() > 1 and position() < last()]//text()")
                    loader.add_xpath('brand', "//a[@class='product-brand']//img/@alt")

                    loader.add_value('url', response.url)

                    price = loader.get_output_value('price')
                    if price < 10:
                        shipping_cost = extract_price('2.95')
                    else:
                        shipping_cost = 0
 
                    # Add shipping cost to product price
                    loader.add_value('shipping_cost', shipping_cost)
                    loader.add_value('price', price + shipping_cost)

                    product = loader.load_item()

                    promotion = response.xpath("//div[@id='product-offer-tab']//h3//text()").extract()
                    metadata = FragranceDirectMeta()
                    if promotion:
                        metadata['promotion'] = promotion[0]
                    if product.get('price'):
                        metadata['price_exc_vat'] = Decimal(product['price']) / Decimal('1.2')
                    product['metadata'] = metadata
                    yield product

            else:
                if not sku:
                    pass
                else:

                    loader = ProductLoader(item=Product(), response=response)
                    price = ''.join(response.xpath('//p[@class="price-info"]//span[@class="Price"]/text()').extract()).strip()
                    if price == '':
                        price = ''.join(response.xpath("//span[@class='Price ']//span[@class='Price-integer' or @class='Price-decimal']//text()").extract())
                    if price == '':
                        self.log("Error! No price! URL: {}".format(response.url))
                        return
                    price = extract_price(price)
                    loader.add_value('url', response.url)

                    loader.add_value('name', product_name)

                    stock = ''.join(response.xpath("//span[@class='stock-level']//text()").extract()).strip()

                    if stock.lower() in ['limited', 'in stock']:
                        stock = '1'
                    else:
                        stock = '0'

                    loader.add_value('stock', stock)

                    loader.add_xpath('category', "//div[@id='breadcrumb']//li[position() > 1 and position() < last()]//text()")
                    loader.add_xpath('brand', "//a[@class='product-brand']//img/@alt")

                    if price < 10:
                        shipping_cost = extract_price('2.95')
                    else:
                        shipping_cost = 0

                    # Add shipping cost to product price
                    loader.add_value('shipping_cost', shipping_cost)
                    loader.add_value('price', price + shipping_cost)

                    loader.add_xpath('sku', "//form[@name='notifications']//input[@name='p']/@value")
                    loader.add_xpath('identifier', "//form[@name='notifications']//input[@name='p']/@value")

                    loader.add_xpath('image_url', "//img/@data-original-large")

                    product = loader.load_item()

                    promotion = response.xpath("//div[@id='product-offer-tab']//h3//text()").extract()
                    metadata = FragranceDirectMeta()
                    if promotion:
                        metadata['promotion'] = promotion[0]
                    if product.get('price'):
                        metadata['price_exc_vat'] = Decimal(product['price']) / Decimal('1.2')
                    product['metadata'] = metadata
                    yield product
