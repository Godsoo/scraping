#-*- coding: utf-8 -*-

import os
import re
import csv
from copy import deepcopy
from urlparse import urljoin
from urllib2 import urlopen

from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http.request import Request
from urlparse import urljoin as urljoin_rfc

from buyagiftitems import BuyAGiftMeta

from product_spiders.base_spiders.primary_spider import PrimarySpider

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

category_codes = {'101': 'Adrenaline',
                  '114': 'Choice Vouchers',
                  '118': 'Days Out',
                  '102': 'Driving',
                  '104': 'Flying',
                  '107': 'Gourmet',
                  '109': 'Hotels',
                  '122': 'Money Vouchers',
                  '119': 'Other',
                  '111': 'Other Activities',
                  '105': 'Pampering',
                  '112': 'Personalized Gifts',
                  '113': 'Personalized Gifts',
                  '115': 'Personalized Gifts'}

search_term_reg = re.compile("(BN-.*)\.aspx")

def extract_search_term_from_url(url):
    m = search_term_reg.search(url)
    if m:
        return m.group(1)
    else:
        return None

product_code_reg = re.compile("br-(.*)\.aspx")

def extract_product_code_from_url(url):
    m = product_code_reg.search(url)
    if m:
        return m.group(1)
    else:
        return None

class BuyAGiftSpider(PrimarySpider):
    name = 'buyagift.co.uk'
    allowed_domains = ['buyagift.co.uk']
    buyagift_filename = os.path.join(HERE, 'buyagift_products.csv')
    start_urls = ('http://www.buyagift.co.uk',)

    csv_file = 'buyagift.co.uk_products.csv'

    def __init__(self, *args, **kwargs):
        super(BuyAGiftSpider, self).__init__(*args, **kwargs)

        self.errors = []

        self.suppliers = {}

        current_product_code = None
        with open(self.buyagift_filename) as f:
            reader = csv.DictReader(f)

            for row in reader:
                product_code = row['Product Code'].decode('utf-8').lower()
                category = row['Category'].decode('utf-8')
                supplier = row['Supplier Name'].decode('utf-8')

                if product_code:
                    if product_code in self.suppliers:
                        self.log("[[TESTING]] ERROR: duplicate product code: %s" % product_code)
                    self.suppliers[product_code] = {
                        'category': category,
                        'suppliers': [supplier]
                    }
                    current_product_code = product_code
                else:
                    if current_product_code:
                        self.suppliers[current_product_code]['suppliers'].append(supplier)

        self.collected = set()
        self.finished = False
                                        
    def _parse_product_el(self, product_el, base_url):
        name = product_el.select('a/div[@class="prd_details"]/h2/text()').extract()[0].strip()
        price = product_el.select('a/div[@class="prd_details"]/div[@class="prd_price_area"]/span/text()').extract()[0].strip()
        price = extract_price(price)
        url = product_el.select("a/@href").extract()[0]
        product_code = extract_product_code_from_url(url).lower()
        image_url = product_el.select('a/span[@class="prd_img"]/img/@data-original').extract()[0]

        loader = ProductLoader(selector=product_el, item=Product())
        loader.add_value('identifier', product_code)
        loader.add_value('sku', product_code)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('url', url)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        category = category_codes.get(product_code[0:3])
        loader.add_value('category', category)
        metadata = BuyAGiftMeta()
        if product_code in self.suppliers:

            supplier_list = self.suppliers[product_code]['suppliers']
            metadata['supplier_name'] = ', '.join(supplier_list)
        product = loader.load_item()
        product['metadata'] = metadata
        self.collected.add(product_code)
        return product

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        self.log("[[TESTING]] Number of suppliers collected: %d" % len(self.suppliers))

        for url in hxs.select("//nav[@id='menu']//li/a/@href").extract():
            url = urljoin(get_base_url(response), url)
            yield Request(url, callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product = response.meta['product']
        forms = hxs.select('//form[contains(@action, "BuyPrintNGo")]')
        image_url = hxs.select('//div[@id="imagegallerymain"]/div//img/@src').extract()
        if image_url:
            product['image_url'] = urljoin_rfc(base_url, image_url[0])
        summary = ' '.join(map(unicode.strip, hxs.select('//*[@id="summary"]//text()').extract())).strip()
        if not summary:
            summary = ''.join(map(unicode.strip, hxs.select('//div[@id="accordion"]//div[contains(@class, "panel-heading") and contains(h4/a/text(), "Summary")]/following-sibling::div//div[contains(@class, "panel-body")]/p/text()').extract())).strip()
        if not summary:
            summary = ''.join(map(unicode.strip, hxs.select('//div[@id="accordion"]//div[contains(@class, "panel-heading") and contains(h4/a/text(), "Summary")]/following-sibling::div//div[contains(@class, "panel-body")]//text()').extract())).strip()
        if not summary:
            summary = ''.join(hxs.select('//*[@id="fine_print"]//*[@class="info_section"]//text()').extract()).strip()
        if 'metadata' in product:
            product['metadata']['summary'] = summary
        else:
            metadata = {}
            metadata['summary'] = summary
            product['metadata'] = metadata
        if not forms:
            yield product
        else:
            for form in forms:
                identifier = form.select('.//input[@name="productCode"]/@value').extract().pop()
                if product['identifier'] != identifier:
                    continue
                for line in form.select('.//table/tr'):
                    item = deepcopy(product)
                    title = line.select('./td[@class="name"]/text()').extract()
                    variant_id = line.select('.//input[contains(@name, "hdnVariantName_")]/@value').extract()
                    price = line.select('.//input[contains(@name, "RP_")]/@value').extract()
                    if title and variant_id and price:
                        item = deepcopy(product)
                        item['name'] = "%s - %s" % (item['name'], title[0])
                        item['identifier'] = "%s-%s" % (identifier, variant_id[0])
                        item['price'] = extract_price(price[0])
                        yield item

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select("//div[@class='category_menu']//li/a/@href").extract():
            url = urljoin(get_base_url(response), url.strip())
            yield Request(url, callback=self.parse_subcategory)
        for item in self.parse_subcategory(response):
            yield item

    def parse_subcategory(self, response):
        hxs = HtmlXPathSelector(response)
        for product in hxs.select('//li[contains(@class, "prd_listing_prod")]'):
            product = self._parse_product_el(product, get_base_url(response))
            yield Request(product['url'], callback=self.parse_product, meta={'product': product})

        # go to page 2
        search_term = urlopen('https://www.buyagift.co.uk/navigation/GetBNNumber?url=%s' %response.url).read()
        if not search_term:
            msg = "[BuyAGift] Error extracting search term from: %s" % response.url
            self.log(msg)
            #self.errors.append(msg)
            return
        search_term = 'BN-' + search_term

        page2_url = "http://www.buyagift.co.uk/navigation/GetPartialRecordsList?searchTerm=%(search_term)s&page=%(page_num)s&pageSize=24&sortTerm=SalesRank&"
        meta = {
            'search_term': search_term,
            'page_num': 2
        }
        page2_url = page2_url % meta
        yield Request(
            page2_url,
            callback=self.parse_pages,
            meta=meta
        )

    def parse_pages(self, response):
        hxs = HtmlXPathSelector(response)
        try:
            products = hxs.select('//li[contains(@class, "prd_listing_prod")]')
        except TypeError:
            return

        for product in products:
            product = self._parse_product_el(product, get_base_url(response))
            yield Request(product['url'], callback=self.parse_product, meta={'product': product})

        if products:
            next_page_url = "http://www.buyagift.co.uk/navigation/GetPartialRecordsList?searchTerm=%(search_term)s&page=%(page_num)s&pageSize=24&sortTerm=SalesRank&"
            meta = {
                'search_term': response.meta['search_term'],
                'page_num': response.meta['page_num'] + 1
            }
            next_page_url = next_page_url % meta
            yield Request(next_page_url, callback=self.parse_pages, meta=meta)
