"""
Kitbag AU account
Fox Soccer Shop spider
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/4982
Spider adds first five products to basket and takes average shipping cost for all products
"""

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request, FormRequest
from decimal import Decimal
import re
import os
import csv
import paramiko
import urllib
import uuid
import json
import itertools
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


option_name_reg = re.compile(r'(.*) \[(.*)\]')

SIZES_DICT = {'xs': 'x small',
              's': 'small',
              'm': 'medium',
              'l': 'large',
              'xl': 'x large',
              '2xl': '2 x large',
              '3xl': '3 x large',
              '4xl': '4 x large ',
              'ys': 'youth small',
              'ym': 'youth medium',
              'yxl': 'youth x large'}


class FoxSoccerShop(CrawlSpider):
    name = 'kitbag_au-foxsoccershop'
    allowed_domains = ['foxsoccershop.com', 'globalshopex.com']
    start_urls = ('http://www.foxsoccershop.com/shop-by-national-team.html',
                  'http://www.foxsoccershop.com/shop-by-club.html')

    categories = LinkExtractor(allow=
                               ('shop-by-national-team',
                                'shop-by-club'))
    products = LinkExtractor(restrict_css='.front_item,.product-link')

    rules = (
        Rule(categories),
        Rule(products, callback='parse_product')
    )

    exchange_rate = None
    shipping_requests = []
    crawled_shipping_request = []
    shipping_costs = []
    items = []
    players = set()

    def __init__(self, *args, **kwargs):
        super(FoxSoccerShop, self).__init__(*args, **kwargs)
        dispatcher.connect(self.idled, signals.spider_idle)

    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = 'gtX34aJy'
        username = 'kitbag'
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        file_path = os.path.join(HERE, 'ExchangeRates.csv')
        sftp.get('Exchange Rates/Exchange Rates.csv', file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Currency'] == 'USD-AUD':
                    self.exchange_rate = extract_price(row['Rate'])
                    break
        self.log('Exchange rate: 1 USD -> {} AUD'.format(self.exchange_rate))

        with open(os.path.join(HERE, 'teams.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['HERO NAME'].lower() != 'n/a' and row['HERO NAME'].lower().strip() != 'williams':
                    self.players.add((row['Merret Department'].decode('utf-8'),
                                      row['HERO NAME'].decode('utf-8'),
                                      row['HERO NUMBER'].decode('utf-8')))

        for url in self.start_urls:
            yield Request(url)

    def make_shipping_request(self, response):
        attributes = response.xpath('//fieldset[@class="attributes"]//li')
        options = []
        for attr in attributes:
            attr_name = attr.xpath('.//input[@name="attrName_1"]/@value').extract()
            if attr_name:
                attr_name = attr_name[0]
            else:
                continue
            attr_options = []
            attr_values = attr.xpath('.//select/option[@value!=""]/@value').extract()
            for attr_value in attr_values:
                attr_options.append((attr_name, attr_value))
            if not attr_values:
                attr_value = attr.xpath('.//input[@name="attrValue_1"]/@value')[0].extract()
                attr_options.append((attr_name, attr_value))
            if attr_options:
                options.append(attr_options)
        options = itertools.product(*options)

        formdata = ()
        formdata += (('index',  response.xpath('//input[@name="index"]/@value')[0].extract()),)
        formdata += (('productId', response.xpath('//input[@name="productId"]/@value')[0].extract()),)
        formdata += (('prodPartNumber_1', response.xpath('//input[@name="prodPartNumber_1"]/@value')[0].extract()),)
        formdata += (('catEntryId_1', response.xpath('//input[@name="catEntryId_1"]/@value')[0].extract()),)
        for option in options:
            for k, v in option:
                formdata += (('attrName_1', k),)
                formdata += (('attrValue_1', v),)
            break
        formdata += (('quantity_1', '1'),)
        body = urllib.urlencode(formdata)
        req = FormRequest.from_response(response, formxpath='//form[@class="order-form"]',
                                        dont_filter=True, callback=self.parse_cart,
                                        meta={'cookiejar': str(uuid.uuid4())})
        req = req.replace(body=body)
        self.shipping_requests.append(req)

    def parse_product(self, response):
        identifier = response.xpath("//div[@class='item-number']/text()").extract_first()
        sku = identifier
        identifier = re.sub(u'a', u'', identifier, flags=re.IGNORECASE)
        name = response.xpath("//div[@class='product-title']/h1/text()").extract_first()
        price = response.xpath("//div[@class='price']//span[@class='disc-price']/text()").extract()
        if not price:
            price = response.xpath("//div[@class='price']/div[@class='regular-price']/span[@class]/text()").extract()
        if price:
            price = price[0].strip('$').replace(",", "")
        else:
            price = '0.00'
        price = Decimal(price)
        # convert using xe.com
        price = price * self.exchange_rate
        image_url = response.xpath("//a[@id='mainImage']/img/@src").extract_first()
        categories = response.xpath('//div[@id="breadcrumbs-"]/ul/li/a//text()')[1:-1].extract()
        try:
            brand = response.xpath('//b[contains(., "BRAND:")]/following-sibling::text()[1]').extract_first().title()
        except AttributeError:
            brand = ''

        attributes = response.xpath('//fieldset[@class="attributes"]//li')
        options = []
        option_names = {}
        for option in response.xpath('//select[@name="attrValue_1"]/option[@value!=""]'):
            opt_val = option.xpath('./@value').extract()
            opt_name = option.xpath('./span/text()').extract()
            if opt_val and opt_name:
                option_names[opt_val[0]] = opt_name[0]
        for attr in attributes:
            attr_name = attr.xpath('.//input[@name="attrName_1"]/@value').extract()
            if attr_name:
                attr_name = attr_name[0]
            else:
                continue
            attr_options = []
            attr_values = attr.xpath('.//select/option[@value!=""]/@value').extract()
            for attr_value in attr_values:
                attr_options.append((attr_name, attr_value))
            if not attr_values:
                attr_value = attr.xpath('.//input[@name="attrValue_1"]/@value')[0].extract()
                attr_options.append((attr_name, attr_value))
            if attr_options:
                options.append(attr_options)
        options = itertools.product(*options)
        items = []
        for option in options:
            opt = [option_names.get(v, '') for _, v in option]
            opt = [o for o in opt if o]
            option_name = ' '.join(opt).strip()
            opt = [SIZES_DICT.get(o.lower(), o) for o in opt]
            option_id = ':'.join(opt).strip()

            option_name = re.sub('size', '', option_name, flags=re.IGNORECASE).strip()
            size = option_names.get(option[-1][-1], '') if option and option[-1] else ''
            size = re.sub('size', '', size, flags=re.IGNORECASE).strip()
            if option_name:
                product_name = name + ' (' + option_name + ')'
            else:
                product_name = name
            if option_id:
                product_identifier = identifier + u':' + option_id.strip().lower()
            else:
                product_identifier = identifier

            loader = ProductLoader(Product(), option)
            loader.add_value('name', product_name)
            loader.add_value('url', response.url)
            loader.add_value('identifier', product_identifier)
            loader.add_value('sku', sku)
            loader.add_value('price', price)
            loader.add_value('image_url', image_url)
            loader.add_value('brand', brand)
            for category in categories:
                loader.add_value('category', category)

            product = loader.load_item()
            product['metadata'] = {'size': size}

            player = [p for p in self.players if p[1].lower() in product_name.lower()]
            if player:
                product['metadata']['player'] = player[0][1].title()
                product['metadata']['number'] = player[0][2]

            if len(self.shipping_requests) < 5:
                self.make_shipping_request(response)
            item = {'item': product}
            item['attributes'] = ()
            for k, v in option:
                item['attributes'] += ((k, v),)
            items.append(item)

        if not options:
            loader = ProductLoader(Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('url', response.url)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('price', price)
            loader.add_value('image_url', image_url)
            loader.add_value('brand', brand)
            for category in categories:
                loader.add_value('category', category)

            product = loader.load_item()
            product['metadata'] = {}
            player = [p for p in self.players if p[1].lower() in name.lower()]
            if player:
                product['metadata']['player'] = player[0][1].title()
                product['metadata']['number'] = player[0][2]

            if len(self.shipping_requests) < 5:
                self.make_shipping_request(response)
            item = {'item': product}
            item['attributes'] = ()
            item['attributes'] += ((response.xpath('//input[@name="attrName_1"]/@value')[0].extract(),
                                    response.xpath('//input[@name="attrValue_1"]/@value')[0].extract()),)
            item['attributes'] += ((response.xpath('//input[@name="attrName_1"]/@value')[1].extract(),
                                    response.xpath('//input[@name="attrValue_1"]/@value')[1].extract()),)
            items.append(item)
        product_id = response.xpath('//input[@name="productId"]/@value')[0].extract()
        yield Request('http://www.foxsoccershop.com/InventoryCheck.json?productId={}'.format(product_id),
                      meta={'items': items},
                      callback=self.parse_stock)

    def parse_stock(self, response):
        data = json.loads(response.body)
        for item in response.meta.get('items'):
            attributes = item.get('attributes')
            it = item.get('item')
            for p in data.get('productItems'):
                correct = True
                for attr in attributes:
                    if p['attributes'].get(attr[0], '') != attr[1]:
                        correct = False
                        break
                if correct and 'out' in p['displayText'].lower():
                    it['stock'] = 0
                    break
            self.items.append(it)

    def parse_cart(self, response):
        url = response.xpath('//a[@id="quick-view-cart-link"]/@href')[0].extract()
        url = response.urljoin(url)
        yield Request(url, callback=self.parse_shipping, meta=response.meta, dont_filter=True)

    def parse_shipping(self, response):
        req = FormRequest.from_response(response, formxpath='//form[@id="ship-est-form"]',
                                        formdata={'country': 'AU', 'shipModeId': '13293'},
                                        callback=self.parse_estimation,
                                        meta=response.meta,
                                        dont_filter=True)
        yield req

    def parse_estimation(self, response):
        shipping_cost = response.xpath('//div[@class="ship-est-result-result"]/text()').re('this order is.(.*)\.')[0]
        self.shipping_costs.append(extract_price(shipping_cost) * self.exchange_rate)
        if len(self.shipping_costs) < 5:
            return
        shipping_cost = sum(self.shipping_costs)/len(self.shipping_costs)
        for item in self.items:
            item['shipping_cost'] = shipping_cost
            yield item
        self.items = []

    def idled(self, spider):
        if spider != self or not self.items:
            return
        for request in self.shipping_requests:
            if request not in self.crawled_shipping_request:
                self.crawled_shipping_request.append(request)
                self.crawler.engine.crawl(request, self)