import re
import os
import csv
import json
import shutil

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter,  add_or_replace_parameter

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class RakutenSpider(BaseSpider):
    name = 'legousa-rakuten.com'
    allowed_domains = ['rakuten.com']

    start_urls = ('http://www.rakuten.com/SR/search/GetSearchResults?mfgid=-1995&from=6',
                  'http://www.rakuten.com/SR/search/GetSearchResults?sid=33&qu=lego&from=6')

    errors = []

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'rakuten_map_deviation.csv')

    def __init__(self, *args, **kwargs):
        super(RakutenSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        if os.path.exists(os.path.join(HERE, 'rakuten_products.csv')):
            shutil.copy(os.path.join(HERE, 'rakuten_products.csv'),
                        os.path.join(HERE, 'rakuten_products.csv.bak'))

    def spider_closed(self, spider, reason):
        shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'rakuten_products.csv'))

    def start_requests(self):
        if os.path.exists(os.path.join(HERE, 'rakuten_products.csv')):
            with open(os.path.join(HERE, 'rakuten_products.csv')) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield Request(row['url'], self.parse_product)

        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        base_url = get_base_url(response)

        data = json.loads(response.body)
        if data:
            products = data['Products']
            for product in products:
                yield Request(urljoin_rfc(base_url, product['ProductUrl']), callback=self.parse_product)
            
            if products:
                page = url_query_parameter(response.url, 'page', '1')
                next_page = add_or_replace_parameter(response.url, 'page', str(int(page)+1))
                yield Request(next_page)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        if hxs.select('//a[@id="anchorUnavailable"]'):
            return

        sellers_url = 'http://www.rakuten.com/PR/SellerListingsAjax.aspx?sku=%s'
        name = hxs.select('//div[@id="product-title"]/h1/text()').extract()[0]
        sku = 0
        for item in re.findall("\d+", name):
            if int(item) > sku:
                sku = int(item)

        if sku == 0 or sku < 100:
            sku = ''.join(hxs.select('//th[contains(text(), "Mfg Part#")]/../td/text()').extract()).strip()

        brand = hxs.select('//th[contains(text(), "Manufacturer")]/../td/a/text()').extract()[0]
        category = hxs.select('//div[@class="product-breadcrumbs"]//a/text()').extract()[-1]
        image_url = hxs.select('//img[@id="productmain"]/@src').extract()
        identifier = hxs.select('//th[contains(text(), "SKU")]/../td/text()').extract()[0]
        price = hxs.select('//div[@class="main-price"]/span[@itemprop="price"]/text()').extract()
        price = price[0] if price else 0
        shipping = hxs.select('//div[@class="main-price"]/span[not(@itemprop="price")]/text()').extract()
        shipping = shipping[0] if shipping else 0
        sellers = hxs.select('//div[@id="seller-contact"]//a[@itemprop="seller"]')
        if sellers:
            yield Request(sellers_url % identifier,
                          callback=self.parse_sellers,
                          meta={'name':name,
                                'brand':brand,
                                'category':category,
                                'identifier': identifier,
                                'sku':sku,
                                'image_url':image_url,
                                'url':response.url})
        else:
            l = ProductLoader(item=Product(), response=response)
            seller_name = hxs.select('//a[@id="anchorMarketplaceShipsFrom"]/text()').extract()
            seller_name = seller_name[0] if seller_name else ''
            if seller_name:
                l.add_value('identifier', identifier + '-' + seller_name)
            else:
                l.add_value('identifier', identifier)
            l.add_value('name', name)
            l.add_value('category', category)
            l.add_value('brand', brand)
            l.add_value('sku', sku)
            l.add_value('url', response.url)
            l.add_value('price', price)
            l.add_value('shipping_cost', shipping)
            l.add_value('image_url', image_url)
            l.add_value('dealer', 'Rak - ' + seller_name if seller_name else '')

            yield l.load_item()

    def parse_sellers(self, response):
        hxs = HtmlXPathSelector(response)
        sellers = hxs.select('//tr[contains(@class,"trMainParent")]')
        meta = response.meta
        total_sellers = len(sellers)
        for seller in sellers:
            price = seller.select('td[@class="sl-td-availability-sec"]/div/div/div/div/text()').extract()[0]
            shipping = seller.select('td[@class="sl-td-availability-sec"]/div/div/div/div/text()').extract()[1]
            seller_name = seller.select('td/div//a[@class="sl-store-link"]/text()').extract()
            if seller_name:
                seller_name = seller_name[0]
            else:
                seller_name = seller.select('td/div[b/text()="Seller:"]/text()').extract()[0]

            l = ProductLoader(item=Product(), response=response)
            if seller_name:
                l.add_value('identifier', meta['identifier'] + '-' + seller_name)
            else:
                l.add_value('identifier', meta['identifier'])

            l.add_value('name', meta['name'])
            l.add_value('category', meta['category'])
            l.add_value('brand', meta['brand'])
            l.add_value('sku', meta['sku'])
            l.add_value('url', meta['url'])
            l.add_value('price', price)
            l.add_value('shipping_cost', shipping)
            l.add_value('image_url', meta['image_url'])
            l.add_value('dealer', 'Rak - ' + seller_name if seller_name else '')

            yield l.load_item()
