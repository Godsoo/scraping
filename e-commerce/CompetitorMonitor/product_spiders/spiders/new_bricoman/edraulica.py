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

from decimal import Decimal
from utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class EDraulicaSpider(BaseSpider):
    name = 'newbricoman-edraulica.it'
    allowed_domains = ('edraulica.it',)
    start_urls = ('http://www.edraulica.it',)
    download_delay = 0

    def __init__(self, *args, **kwargs):
        super(EDraulicaSpider, self).__init__(*args, **kwargs)
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
        categories = hxs.select(u'//li/a[not(contains(@href,"javascript"))]/@href').extract()
        for url in categories:
            url = urljoin_rfc(base_url, url)
            yield Request(url)
        next_page = hxs.select(u'//table[@class="CPpageNav"]//a[descendant::font[text()="Avanti"]]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(base_url, next_page[0])
            yield Request(next_page)
        for product in self.parse_product(response):
            yield product

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        category = u' > '.join(hxs.select(u'//td[@class="CPpageHead"]//a/b/font[text()]/text()').extract())
        products = hxs.select(u'//table//tr[child::td[child::a[child::b[@class="CPprodDesc"]]]]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            url = product.select(u'.//td/a[b]/@href')[0].extract()
            url = urljoin_rfc(base_url, url)
            loader.add_value('url', url)
            name = product.select(u'.//td/a/b/text()')[0].extract().strip()
            loader.add_value('name', name)
            loader.add_value('category', category)
            identifier = re.search(u'/(\d{3,})/', url).group(1)
            loader.add_value('identifier', identifier)
            price = product.select(u'.//b[@class="CPprodPriceV"]/text()').re(u'[\d\.,]+')[0].replace(u',', u'')
            loader.add_value('price', price)
            image_url = product.select(u'.//table[@align="center"]//td[@align="center"]//img/@src').extract()
            if image_url:
                image_url = urljoin_rfc(base_url, image_url[0])
                loader.add_value('image_url', image_url)

            price = extract_price(price)

            if price < Decimal(490.9):
                loader.add_value('shipping_cost', '9.90')

            yield Request(url, callback=self.parse_details, meta={'loader': loader})

    def parse_details(self, response):
        hxs = HtmlXPathSelector(response)
        loader = response.meta.get('loader')
        details = hxs.select('//div[@class="TabbedPanelsContentGroup"]/div/div[@class="boxEtichetta" or @class="boxValore"]/p/text()').extract()
        details = dict(zip(details[0::2], details[1::2]))

        loader.add_value('sku', details.get('MODELLO', ''))
        loader.add_value('brand', details.get('MARCA', ''))
        yield loader.load_item()
