import re
import json
import os
import csv
import shutil

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from urlparse import urljoin
from urllib2 import urlopen
from product_spiders.utils import extract_price

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from decimal import Decimal

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

HERE = os.path.abspath(os.path.dirname(__file__))

class SearsSpider(BaseSpider):
    name = 'legousa-sears.com'
    allowed_domains = ['sears.com']
    start_urls = ('http://www.sears.com',)
    
    json_url = 'http://www.sears.com/service/search/productSearch?catalogId=12605&catgroupId=1020010&catgroupIdPath=1020010&levels=Toys+%26+Games&primaryPath=Toys+%26+Games&sbf=Brand&sbv=LEGO&searchBy=subcategory&storeId=10153&subCatView=true&tabClicked=All'
    price_url = 'http://www.sears.com/content/pdp/products/pricing/v1/get/price/display/json?pid=%s&pidType=0&priceMatch=Y&memberStatus=G&storeId=10153'
    product_url = 'http://www.sears.com/content/pdp/config/products/v1/products/%s?site=sears'
    sellers_url = 'http://www.sears.com/content/pdp/sellers/%s'
    
    def start_requests(self):        
        yield Request(self.json_url, callback=self.parse_json)
        for page_number in xrange(2, 50):
            yield Request(self.json_url+'&pageNum=%s'%str(page_number), callback=self.parse_json, meta={'dont_redirect':True})
            
    def parse_json(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        data = json.loads(response.body)
        for product in data['data']['products']:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('identifier', product['partNumber'])
            loader.add_value('sku', product['mfgPartNum'])
            loader.add_value('name', product['name'])
            loader.add_value('url', urljoin(base_url, product['url']))
            loader.add_value('brand', product['brandName'])
            loader.add_value('image_url', product['image'])
            
            url = self.price_url %product['partNumber']
            price = json.loads(urlopen(url).read())['priceDisplay']['response'][0]['finalPrice']['numeric']
            loader.add_value('price', price)
            item = loader.load_item()
            
            url = self.product_url %product['sin']
            yield Request(url, callback=self.parse_product, meta={'dont_redirect': True, 'loader':ProductLoader(item=item, selector=hxs)})

    def parse_product(self, response):
        product_data = json.loads(response.body)['data']
        category = product_data['productmapping']['primaryWebPath'][-1]['name']
        loader = response.meta['loader']
        loader.add_value('category', category)
        try:
            loader.add_value('dealer', product_data['offer']['ffm']['soldBy'])
            loader.add_value('shipping_cost', product_data['offer']['shipping']['minRate'])
        except:
            pass
        
        item = loader.load_item()
        identifier = item['identifier']
        
        uid = product_data['productstatus']['uid']
        url = self.sellers_url %uid
        try:
            sellers = json.loads(urlopen(url).read())['groups'][0]['offers']
        except:
            yield item
            return
        for seller in sellers:
#                self.log('Seller is %s from %s' %(seller, product['partNumber']))
            shipping_price = seller.get('shippingPrice', 0)
            item['price'] = extract_price(str(seller['totalPrice'] - shipping_price))
            item['shipping_cost'] = shipping_price
            item['identifier'] = identifier + '-' + seller['sellerId']
            try:
                item['dealer'] = seller['sellerName']
            except:
                item['dealer'] = seller['sellerId']
            yield item

    

"""
class SearsSpider(BaseSpider):
    name = 'legousa-sears.com'
    allowed_domains = ['sears.com']
    start_urls = ('http://www.sears.com',)

    errors = []
    ids = []

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'sears_map_deviation.csv')
    map_screenshot_method = 'scrapy_response'

    def __init__(self, *args, **kwargs):
        super(SearsSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self.all_products_filename = os.path.join(HERE, 'sears_products.csv')

        if os.path.exists(self.all_products_filename):
            shutil.copy(self.all_products_filename,
                        self.all_products_filename + '.bak')

        self.map_screenshot_html_files = {}

    def spider_closed(self, spider):
        shutil.copy('data/%s_products.csv' % spider.crawl_id, self.all_products_filename)

    def start_requests(self):
        cookies = {'IntnlShip': 'US|USD|1|12425778|||N'}

        yield Request('http://www.sears.com', callback=self.parse_sears, cookies=cookies)

    def parse_sears(self, response):
        categories_url = 'http://www.sears.com/toys-games/b-1600000004?lang=en&sbf=Brand&sbv=LEGO'

        lego_urls = ['http://www.sears.com/search=lego&LEGO?filter=Brand&keywordSearch=false&vName=Toys+%26+Games&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&viewItems=50&storeId=10153',
                     'http://www.sears.com/search=lego&LEGO?lang=en&filter=Brand&keywordSearch=false&catalogId=12605&previousSort=ORIGINAL_SORT_ORDER&intShip=1&viewItems=50&storeId=10153',
                     'http://www.sears.com/search=lego?redirectType=CAT_REC_PRED&viewItems=50&autoRedirect=true&storeId=10153&levels=Toys+%26+Games_Blocks+%26+Building+Sets_Building+Sets',
                     'http://www.sears.com/toys-games-blocks-building-sets-building-sets/s-1029063?keyword=lego&autoRedirect=true&viewItems=50&redirectType=CAT_REC_PRED',
                     'http://www.sears.com/toys-games-blocks-building-sets-building-sets&LEGO/b-1029063?filter=Brand&keywordSearch=false&previousSort=ORIGINAL_SORT_ORDER&viewItems=50',
                     'http://www.sears.com/toys-games-blocks-building-sets-building-sets/b-1029063?sbf=Brand&sbv=LEGO&viewItems=50',
                     'http://www.sears.com/shc/s/toys-games-blocks-building-sets-building-sets/b-1029063?keyword=lego&viewItems=50&autoRedirect=true&redirectType=CAT_REC_PRED',
                     'http://www.sears.com/toys-games-blocks-building-sets-blocks/b-1021032?sbf=Brand&sbv=LEGO',
                     'http://www.sears.com/toys-games/b-1020010?sbf=Brand&sbv=LEGO',
                     ]

        if os.path.exists(self.all_products_filename):
            with open(self.all_products_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield Request(row['url'],
                                  callback=self.parse_product)

        # Scrape start urls
        for url in self.start_urls:
            yield Request(url, meta={'real_crawl': True})

        for lego_url in lego_urls:
            yield Request(lego_url, callback=self.parse_lego)

        yield Request(categories_url, callback=self.parse_categories)


    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[contains(@class, "item")]/h4/a/@href').extract() + \
            hxs.select('//div[@class="ddlContainer"]/div[@class="ddlList"]//a/@href').extract() + \
            hxs.select("//dl[@id='categories_menu']/dd/h2/a/@href").extract()
        if categories:
            for url in filter(lambda u: u not in response.url and 'lego' in u.lower(), categories):
                yield Request(add_or_replace_parameter(urljoin_rfc(base_url, url), 'viewItems', '50'),
                              callback=self.parse_lego)

        if not categories:
            self.errors.append('WARNING: No categories => %s' % response.url)

    def parse_lego(self, response):
        if 'lego' not in response.url.lower():
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = [url for url in \
                      hxs.select('//div[@itemprop="significantLinks" and '
                                 'contains(@id, "FeaturedSubCats")]/ul//a/@href')
                      .extract() if url]
        for url in filter(lambda u: 'lego' in u.lower(), categories):
            yield Request(add_or_replace_parameter(urljoin_rfc(base_url, url), 'viewItems', '50'),
                          callback=self.parse_lego)

        products = hxs.select('//div[@id="cardsHolder"]//h2[@itemprop="name"]/a/@href').extract()
        for product_url in products:
            url = urljoin_rfc(base_url, product_url)
            yield Request(url, callback=self.parse_product)

        pages = hxs.select('//select[@id="pagination"]/option/@value').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_lego)

        next = hxs.select('//div[@id="srchPagination"]/a/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[-1]), callback=self.parse_lego)

        if not categories and not products:
            # self.errors.append('WARNING: No products and No categories => %s' % response.url)
            # Try parse product page
            for item in self.parse_product(response):
                yield item

        if len(products) == 50 and not next:
            self.errors.append('WARNING: no next page => %s' % response.url)

        if len(products) < 50 and next:
            self.log('>>> Too few products in %s' % response.url)
            retry = response.meta.get('retry', 0)
            if retry < 10:
                meta = response.meta.copy()
                meta['retry'] = retry + 1
                yield Request(response.url,
                              meta=meta,
                              callback=self.parse_lego,
                              dont_filter=True)

    def parse_product(self, response):
        if 'lego' not in response.url.lower() or 'p-' not in response.url.lower():
            return
        hxs = HtmlXPathSelector(response)
        sku = ''
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()
        json_url = "http://www.sears.com/content/pdp/config/products/v1/products/%s?site=sears"
        prod_id = response.url.split('p-')[-1].split('?')[0]

        try:
            seller_name = ' '.join(hxs.select('//p[@class="ffmentStoreName"]/text()').extract()[0].split())
        except:
            try:
                seller_name = hxs.select('//span[@id="vendorName2"]/a[@class="merchantNameLink"]/text()').extract()[0].strip()
            except:
                seller_name = ''

        dealer = 'Sears - ' + seller_name if seller_name else ''

        try:
            identifier = hxs.select('//input[@id="partnumber"]/@value').extract()[0].strip()
        except:
            identifier = ''

        price = hxs.select('//div[@class="youPay bl"]/span[@class="pricing"]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="truePrice"]/text()').extract()
        if price:
            price = price[0]
        else:
            price = hxs.select('//div[@class="youPay"]/span[@class="pricing"]/text()').extract()
            price = price[0].strip() if price else 0

        yield Request(json_url % prod_id, callback=self.parse_json,
                      meta={'url':response.url,
                            'dealer': dealer,
                            'identifier': identifier,
                            'price': price})

    def parse_json(self, response):
        data = json.loads(response.body)
        product = data['data']['product']
        product_status = data['data']['productstatus']
        
        if product_status['isDeleted']:
            return
        
        sellers_url = 'http://www.sears.com/content/pdp/sellers/%(uid)s'

        l = ProductLoader(item=Product(), response=response)

        identifier = product['id']

        sku = 0
        name = product['name']
        for item in re.findall("\d+", name):
            if int(item) > sku:
                sku = int(item)

        if sku == 0 or sku < 100:
            sku = product.get('mfr', {'modelNo': ''}).get('modelNo')

        l.add_value('name', name)

        if sku:
            l.add_value('sku', sku)

        try:
            l.add_value('category', product['taxonomy']['web']['sites']['sears']['hierarchies'][0]['specificHierarchy'][-1]['name'])
        except:
            pass
        l.add_value('brand', product['brand']['name'])
        l.add_value('category', '')
        l.add_value('url', response.meta['url'].split('?')[0])
        l.add_value('identifier', response.meta['identifier'])
        l.add_value('dealer', response.meta['dealer'])
        l.add_value('price', response.meta['price'])
        try:
            l.add_value('image_url', product['assets']['imgs'][0]['vals'][0]['src'])
        except:
            pass


        item = l.load_item()

        try:
            yield Request(sellers_url % product_status,
                          meta={'item': item,
                                'handle_httpstatus_list': [404],
                                'dont_retry': True},
                          callback=self.parse_sellers)
        except:
            for attr in data['data']['attributes']['variants']:
                yield Request(sellers_url % {'uid': attr['uid']},
                              meta={'item': item,
                                    'handle_httpstatus_list': [404],
                                    'dont_retry': True},
                              callback=self.parse_sellers)

    def parse_sellers(self, response):
        item = response.meta.get('item')

        if response.status == 404:
            if item.get('identifier') and item.get('price'):
                yield item
            return

        sellers_data = json.loads(response.body)

        offers = sellers_data['groups'][0]['offers']
        for offer in offers:
            product = Product(item)
            product['identifier'] = offer['id']
            try:
                product['dealer'] = 'Sears - ' + offer['sellerName']
            except:
                seller_id = offer['sellerId']
                if 'SEARS' == seller_id.upper():
                    product['dealer'] = seller_id
                else:
                    product['dealer'] = 'Sears - ' + offer['sellerId']
            total_price = float(offer['totalPrice'])
            try:
                shipping_price = float(offer['shippingPrice'])
            except:
                shipping_price = float(0.0)
            product['shipping_cost'] = Decimal(str(shipping_price))
            product['price'] = Decimal(str(round(total_price - shipping_price, 2)))

            yield product
"""
