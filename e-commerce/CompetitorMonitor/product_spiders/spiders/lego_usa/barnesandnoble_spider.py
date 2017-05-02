import re
import json
import os
import csv
import shutil

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.spiders.BeautifulSoup import BeautifulSoup
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class BarnesAndNobleSpider(BaseSpider):
    name = 'legousa-barnesandnoble.com'
    allowed_domains = ['barnesandnoble.com']
    start_urls = ('http://www.barnesandnoble.com/s/%22LEGO%22?Ntk=Publisher&Ns=P_Sales_Rank&Ntx=mode+matchall',)

    user_agent = 'Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0'

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'barnesandnoble_map_deviation.csv')

    def __init__(self, *args, **kwargs):
        super(BarnesAndNobleSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        shutil.copy(os.path.join(HERE, 'barnesandnoble_products.csv'),
                    os.path.join(HERE, 'barnesandnoble_products.csv.bak'))

        # Errors
        self.errors = []

    def spider_closed(self, spider):
        shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'barnesandnoble_products.csv'))

    def start_requests(self):
        # Parse default items and then start_urls
        yield Request('http://www.barnesandnoble.com/', self.parse_default)

    def parse_default(self, response):
        with open(os.path.join(HERE, 'barnesandnoble_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request(row['url'],
                              callback=self.parse_product,
                              meta={'dont_merge_cookies': True})

        # Scrape start urls
        for url in self.start_urls:
            yield Request(url, meta={'dont_merge_cookies': True})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = response.css('.product-info a::attr(href)').extract()
        for product_url in products:
            yield Request(urljoin_rfc(base_url, product_url),
                          callback=self.parse_product)

        next_page = response.xpath('//a[span[@class="next-page"]]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[-1]))

        if not products and not next_page:
            self.errors.append('WARNING: No products and not next page in %s' % response.url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        try:
            name = response.xpath('//section[@id="prodSummary"]/h1/text()').extract()[0].strip()
        except:
            retry = int(response.meta.get('retry', 0))
            if retry < 5:
                retry += 1
                yield Request(response.url,
                              meta={'retry': retry, 'dont_merge_cookies': True},
                              callback=self.parse_product,
                              dont_filter=True)
            return
        ean = response.url.split('ean=')[-1]
        identifier = str(int(ean))
        sku = 0
        for item in re.findall("\d+", name):
            if int(item) > sku:
                sku = int(item)

        if sku == 0 or sku < 100:
            sku = None

        brand = 'LEGO'

        category = 'LEGO'
        image_url = response.xpath('//img[@id="pdpMainImage"]/@src').extract()
        image_url = 'http:' + image_url[0].strip() if image_url else ''

        price = response.xpath('//aside[@id="prodInfoContainer"]/p[@class="price"]/text()').extract()
        price = price[0].strip() if price else 0
        sellers = response.xpath('//h3[contains(text(), "marketplace")]')
        if sellers:
            sellers_url = 'http://www.barnesandnoble.com/xhr/handler.jsp?productId=prd%s&service=marketplace-items'
            yield Request(sellers_url % ean,
                          callback=self.parse_sellers,
                          meta={'name':name,
                                'image_url':image_url,
                                'identifier':identifier,
                                'category':category,
                                'brand':brand,
                                'url': response.url,
                                'sku':sku,
                                'price':price,
                                'dont_merge_cookies': True})
        else:
            l = ProductLoader(item=Product(), response=response)
            seller_name = 'Barnes And Noble'
            l.add_value('identifier', identifier + '-' + seller_name)
            l.add_value('name', name)
            l.add_value('category', category)
            l.add_value('brand', brand)
            if sku:
                l.add_value('sku', sku)
            l.add_value('url', response.url)
            l.add_value('price', price)
            l.add_value('shipping_cost', 0)
            l.add_value('image_url', image_url)
            l.add_value('dealer', 'B&N - ' + seller_name if seller_name else '')
            yield l.load_item()

    def parse_sellers(self, response):
        meta = response.meta
        json_data = json.loads(response.body)


        sellers = json_data['service']['items']

        total_sellers = len(sellers) + 1
        if meta['price']:
            seller_name = 'Barnes And Noble'
            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', meta['identifier'] + '-' + seller_name)
            l.add_value('name', meta['name'])
            l.add_value('category', meta['category'])
            l.add_value('brand', meta['brand'])
            if meta['sku']:
                l.add_value('sku', meta['sku'])
            l.add_value('url', meta['url'])
            l.add_value('price', meta['price'])
            l.add_value('image_url', meta['image_url'])
            l.add_value('dealer', 'B&N - ' + seller_name if seller_name else '')

            yield l.load_item()


        for seller in sellers:
            price = seller['bnPrice']
            seller_name = seller['sellerName']

            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', meta['identifier'] + '-' + seller_name)
            l.add_value('name', meta['name'])
            l.add_value('category', meta['category'])
            l.add_value('brand', meta['brand'])
            if meta['sku']:
                l.add_value('sku', meta['sku'])
            l.add_value('url', meta['url'])
            l.add_value('price', price)
            l.add_value('image_url', meta['image_url'])
            l.add_value('dealer', 'B&N - ' + seller_name if seller_name else '')

            yield l.load_item()

        if not sellers:
            retry = int(response.meta.get('try', 0))
            if retry < 10:
                meta = response.meta.copy()
                meta['try'] = retry + 1
                meta['dont_merge_cookies'] = True
                self.log('>>> NO SELLERS FOUND IN %s => RETRY No. %s' % (response.url, str(meta['try'])))
                yield Request(response.url,
                              meta=meta,
                              callback=self.parse_sellers,
                              dont_filter=True)
