"""
Account: Angling Direct
Original ticket: https://app.assembla.com/spaces/competitormonitor/tickets/5370-angling-direct-%7C-gerrys-fishing-%7C-new-site/details
Extract all items and options
"""

import csv
import os
import time
import re
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from product_spiders.config import DATA_DIR


def get_session_id(response):
    headers = response.headers.getlist('Set-Cookie')
    for header in headers:
        session_id = re.search('JSESSIONID=(.*-jvm)', header)
        if session_id:
            return session_id.group(1)

class GerrysFishingSpider(BaseSpider):
    name = 'angling_direct-gerrysfishing.com'
    allowed_domains = ['gerrysfishing.com']
    start_urls = ('http://www.gerrysfishing.com',)
    options_url = 'http://www.gerrysfishing.com/template/components/stockdetailoptionlist.jsp?emptytxt=[choose%20Vass]&optlevkey={key}&_={t}'
    add_to_basket_url = 'http://www.gerrysfishing.com/template/components/stocklistingaddtobasket.jsp?seq=30000&qty=1&vaId={identifier}&type=3&_={t}'
    basket_url = 'http://www.gerrysfishing.com/basket.jsp'
    rotate_agent = True
    product_data = {}

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            with open(filename) as f:
                for row in csv.DictReader(f):
                    self.product_data[row['identifier']] = {'brand': row['brand'], 'shipping_cost': row['shipping_cost']}
        for url in self.start_urls:
            yield Request(url, meta={'dont_merge_cookies': True})

    def parse(self, response):
        categories = response.xpath('//div[@id="nav"]//a/@href').extract()
        categories += response.xpath('//li[@class="groupname"]/a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url),
                          meta={'dont_merge_cookies': True})

        next_page = response.xpath('//a[@id="nextpagebutton"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]),
                          cookies={},
                          meta={'dont_merge_cookies': True})

        products = response.xpath('//li[@class="productThumbName"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product,
                          meta={'dont_merge_cookies': True},
                          cookies={})

    def parse_product(self, response):
        parse_options = not response.meta.get('options', False)
        multioptions = response.xpath('//select[@name="optlev4id"]/option[@value!="0"]/@value').extract()
        if multioptions and parse_options:
            for op in multioptions:
                opkey = '{}---'.format(op)
                req = Request(self.options_url.format(key=opkey, t=int(time.time()*1000)),
                              callback=self.parse_options,
                              meta={'opcodes': [op],
                                    'response': response})
                req.cookies['JSESSIONID'] = get_session_id(response)
                yield req
            return

        options = response.xpath('//div[@id="productoptionselection"]/select[@name="id"]/option[@value!="0"]/@value').extract()
        if options and parse_options:
            for op in options:
                formdata = {'updbasket': '0', 'id': op}
                req = FormRequest.from_response(response, formname='qtyform',
                                                formdata=formdata, callback=self.parse_product,
                                                meta={'options': True,
                                                      'dont_merge_cookies': True},)
                yield req
            return

        loader = ProductLoader(item=Product(), response=response)

        categories = response.xpath('//div[@class="pagetopnav"]//ul[@class="crumb blocklist"]/li/a/text()')[1:-1].extract()
        for category in categories:
            loader.add_value('category', category)

        image_url = response.xpath('//img[@class="productMain"]/@src').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))
        loader.add_value('url', response.url)
        name = response.xpath('//div[@class="detailInfo"]/h1/text()')[0].extract().strip()
        loader.add_value('name', name)
        sku = response.xpath('//div[@id="productcode"]/text()').re('Code: (.*)')
        loader.add_value('sku', sku)
        identifier = response.xpath('//div[@id="productoptionselection"]/select[@name="id"]/option[@selected]/@value').extract()
        if not identifier or (identifier and identifier[0] == '0'):
            identifier = response.xpath('//input[@name="id"]/@value').extract()
        loader.add_value('identifier', identifier)
        prod_data = self.product_data.get(identifier[0]) if identifier[0] in self.product_data else None
        price = response.xpath('//span[@class="detailOurPrice"]/strong/text()').extract()
        if not price:
            price = response.xpath('//div[@class="productprice "]/strong/text()').extract()
        if not price:
            price = ['0.00']
        loader.add_value('price', price)
        stock = response.xpath('//li[@class="stockStatus"]/text()').re('In Stock')
        if not stock:
            loader.add_value('stock', 0)
        brand = re.search(u'Brands > (.*)', u' > '.join(categories))
        if brand:
            loader.add_value('brand', brand.group(1))
        elif prod_data is not None:
            loader.add_value('brand', prod_data.get('brand', ''))

        if not options or not parse_options:
            item = loader.load_item()
            if extract_price(price[0]) >= Decimal('100'):
                item['shipping_cost'] = '0.00'
                yield item
                return
            if prod_data is not None and prod_data.get('shipping_cost'):
                item['shipping_cost'] = prod_data.get('shipping_cost')
                yield item
                return
            session_id = get_session_id(response)
            req = FormRequest(self.add_to_basket_url.format(identifier=identifier[0], t=str(int(time.time()*1000))),
                              callback=self.parse_shipping, meta={'item': item, 'session_id': session_id})
            req.headers['X-Requested-With'] = 'XMLHttpRequest'
            req.cookies['JSESSIONID'] = session_id
            yield req

    def parse_options(self, response):
        opcodes = response.meta.get('opcodes', [])
        prod_response = response.meta.get('response')
        options = response.xpath('//select/option[@value!="0"]/@value').extract()
        for op in options:
            opkey = opcodes + [op]
            opkey += [''] * (4 - len(opkey))
            opkey = '-'.join(opkey)
            yield Request(self.options_url.format(key=opkey, t=int(time.time()*1000)),
                          callback=self.parse_options,
                          meta={'opcodes': opcodes + [op],
                                'response': prod_response,
                                'dont_merge_cookies': True})
        if not options:
            formdata = {'updbasket': '0', 'id': opcodes[-1]}
            yield FormRequest.from_response(prod_response, formname='qtyform',
                                            formdata=formdata, callback=self.parse_product,
                                            meta={'options': True,
                                                  'dont_merge_cookies': True})

    def parse_shipping(self, response):
        req = Request(self.basket_url, meta=response.meta, callback=self.parse_shipping_price, dont_filter=True)
        req.cookies['JSESSIONID'] = response.meta.get('session_id')
        yield req

    def parse_shipping_price(self, response):
        shipping_cost = response.xpath('//ul[contains(@class,"majorbasketdeliverytotal")]/li[@class="subtotalamount"]/text()').extract()
        item = response.meta.get('item')
        item['shipping_cost'] = extract_price(shipping_cost[0])
        yield item
