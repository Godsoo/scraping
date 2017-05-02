import os
import shutil
import csv
import re

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class NetAPorterSpider(BaseSpider):
    name = 'mytheresa-net-a-porter.com'
    allowed_domains = ['net-a-porter.com']
    start_urls = ('http://www.net-a-porter.com',)

    products_file = os.path.join(HERE, 'netaporter_products.csv')

    def __init__(self, *args, **kwargs):
        super(NetAPorterSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self.exchange_rate = 1

    def spider_closed(self, spider):
        """
        On full run saves crawl results for future use if it's full run then.
        """
        self.log("Saving crawl results")
        shutil.copy('data/%s_products.csv' % spider.crawl_id, self.products_file)

    def start_requests(self):
        params = {'channel': 'INTL',
                  'country': 'DE',
                  'httpsRedirect': '',
                  'language': 'en',
                  'redirect': ''}

        req = FormRequest(url="http://www.net-a-porter.com/intl/changecountry.nap?overlay=true",
                          formdata=params)
        yield req

    def parse(self, response):
        start_urls = [
            'http://www.net-a-porter.com/Shop/Bags?level3Filter=&pn=1&npp=60&image_view=product&dScroll=785&designerFilter=122;260;290;517;128&excludeFilters=false',
            'http://www.net-a-porter.com/Shop/Clothing?level3Filter=&pn=1&npp=60&image_view=product&dScroll=0&designerFilter=171;404;449;502;661&excludeFilters=false',
            'http://www.net-a-porter.com/Shop/Shoes?level3Filter=&pn=1&npp=60&image_view=product&dScroll=1332&designerFilter=1474;285;398;4;72;128;1442&sizeScheme=IT',
            'http://www.net-a-porter.com/Shop/Accessories?level3Filter=&pn=1&npp=60&image_view=product&dScroll=1667&designerFilter=171;285;449;88&excludeFilters=false',
        ]

        for url in start_urls:
            yield Request(url, callback=self.parse_category)

        if os.path.exists(self.products_file) and os.path.isfile(self.products_file):
            with open(self.products_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    meta = {
                        'category': row['category'],
                        'brand': row['brand'],
                        'sku': row['sku'],
                        'url': row['url']
                    }
                    yield Request(row['url'], callback=self.parse_product, meta=meta)

    def parse_category(self, response):
        base_url = get_base_url(response)

        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="description"]/a/@href').extract()
        for product in products:
            category = hxs.select('//div[@class="product-list-title"]/h1/a/text()').extract()[0]
            url = urljoin_rfc(base_url, product)
            yield Request(url, callback=self.parse_product, meta={'category': category})

        for url in hxs.select('//div[@class="pagination-links"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        colour = re.findall(r'colour = "(.*)",', response.body)

        l = ProductLoader(item=Product(), response=response)

        brand = hxs.select('//h2[@itemprop="brand"]/a/text()').extract()[0]
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        if colour:
            name += ' ' + colour[0].strip()
        l.add_value('name', brand + ' ' + name)
        l.add_value('url', response.url)
        sku = hxs.select('//meta[@itemprop="sku"]/@content').extract()
        sku = sku[0] if sku else ''
        l.add_value('sku', sku)
        l.add_value('identifier', sku)
        l.add_value('brand', brand)
        image_url = hxs.select('//img[@id="medium-image"]/@src').extract()
        if image_url:
            l.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        l.add_value('category', meta.get('category'))
        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        if price:
            price = extract_price(price[0])
        else:
            price = 0
        l.add_value('price', price)
        if l.get_output_value('price') < 300:
            l.add_value('shipping_cost', 15)
        in_stock = hxs.select('//input[@class="primary-button add-to-bag"]')
        if not in_stock:
            l.add_value('stock', 0)
        yield l.load_item()
