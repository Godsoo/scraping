import re
import csv
import os
import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class ElettroNewSpider(BaseSpider):
    name = 'newbricoman-elettronew.it'
    allowed_domains = ('elettronew.it', 'elettronew.com')
    start_urls = ('http://www.elettronew.com/index.php',)
    download_delay = 0

    def __init__(self, *args, **kwargs):
        super(ElettroNewSpider, self).__init__(*args, **kwargs)
        self.ean_codes = {}
        self.model_codes = {}
        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('EAN', None):
                    self.ean_codes[row['EAN']] = row['Code']
                if row.get('model', None):
                    self.model_codes[row['model'].lower()] = row['EAN']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        categories = set(hxs.select(u'//div[@align="left"]/a[contains(@href,"prodotti")]/@href').extract())
        for url in categories:
            url = url.replace('../', '')
            yield Request(urljoin_rfc(base_url, url))
        next_page = []  # hxs.select(u'//table[@class="CPpageNav"]//a[descendant::font[text()="Avanti"]]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(base_url, next_page[0].replace('../', ''))
            yield Request(next_page)
        for product in self.parse_product(response):
            yield product

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        category = u' > '.join(hxs.select(u'//td/div[@align="left"]/a[contains(@href,"prodotti")]/b/text()').extract())
        products = hxs.select(u'//td[strong[font] and b/a]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            url = product.select(u'.//b/a/@href')[0].extract()
            url = urljoin_rfc(base_url, url)
            loader.add_value('url', url)
            name = product.select(u'.//b/a/text()')[0].extract().strip()
            loader.add_value('name', name)
            loader.add_value('category', category)
            identifier = product.select('a[contains(@id, "modo")]/@id').re(r'modo(.*)')
            loader.add_value('identifier', identifier)
            sku = product.select(u'.//font/text()').re(u'Cod\. (.*)')[0]
            loader.add_value('sku', sku)
            price = product.select(u'.//strong/font/text()').re(u'[\d\.,]+')[0].replace(u',', u'')
            loader.add_value('price', price)
            image_url = product.select(u'.//a/img/@src').extract()
            if image_url:
                image_url = urljoin_rfc(base_url, image_url[0])
                loader.add_value('image_url', image_url)
            loader.add_value('shipping_cost', '10.00')

            item = loader.load_item()
            if item['price']:
                yield loader.load_item()
