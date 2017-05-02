import re
import csv
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

CSV_FILENAME = os.path.join(os.path.dirname(__file__), 'maxoutil.csv')


def normalize_name(name):
    return re.sub(' +', ' ', name).strip().lower()


def normalize_url(url):
    reg = r'%([0-9A-F][0-9A-F])'
    res = url
    m = re.search(reg, res)
    while m:
        found = m.group(0)
        char = chr(int(m.group(1), 16))
        res = res.replace(found, char)
        m = re.search(reg, res)
    return res


class MaxoutilSpider(BaseSpider):
    name = 'maxoutil.com'
    allowed_domains = ['maxoutil.com', 'www.maxoutil.com']
    start_urls = ('http://www.maxoutil.com/outillage-electroportatif.html?dir=asc&order=name&limit=30',
                  'http://www.maxoutil.com/consommables-et-accessoires?limit=30',
                  'http://www.maxoutil.com/outillage-a-main.html?dir=asc&order=name&limit=30',
                  'http://www.maxoutil.com/fixation.html?dir=asc&order=name&limit=30',
                  'http://www.maxoutil.com/quincaillerie-de-batiment.html?dir=asc&order=name&limit=30',
                  'http://www.maxoutil.com/gros-oeuvre-et-manutention.html?dir=asc&order=name&limit=30')

    def __init__(self, *args, **kwargs):
        super(MaxoutilSpider, self).__init__(*args, **kwargs)
        self.names = {}
        with open(CSV_FILENAME) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.names[normalize_name(row['name'])] = row['name']

        self.identifiers_collected = set()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        category = response.xpath('//div[@class="breadcrumbs"]//a/span/text()').extract()[1:]
        identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
        image_url = hxs.select('//div[@class="product-img-box"]/a[@id="main-image"]/img/@src').extract()
        name = normalize_name(hxs.select('//h1/text()').extract()[0])
        price = "".join(hxs.select('//div[@class="product-view"]//div[@class="price-box"]//span[contains(@id, "price-including-tax-")]//text()').extract()).replace(',', '.').replace(u'\xa0', "").strip()
        sku = hxs.select('//*[@itemprop="sku"]/text()').extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        if category:
            loader.add_value('category', category[0])
        if image_url:
            loader.add_value('image_url', image_url[0])

        loader.add_value('stock', 1)

        item = loader.load_item()

        if not item['identifier'] in self.identifiers_collected:
            self.identifiers_collected.add(item['identifier'])
            yield item

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="category-products"]//div[contains(@class, "pdName")]//a/@href').extract()

        for url in products:
            yield Request(url, callback=self.parse_product)

    def parse_products(self, response):
        "Not used for now"
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="category-products"]//li[contains(@class, "item")]')
        if not products:
            return
        category = hxs.select('//div[contains(@class, "category-title")]/h1/text()').extract()[0].replace('\t', '')

        for product in products:
            try:
                name = product.select('.//h3/a/@title').extract()[0]
                name = normalize_name(name)
                name = self.names.get(name, name)
                url = product.select('.//h3/a/@href').extract()[0]
                identifier = product.select('.//button[@class="button btn-cart"]/@onclick').re('product/(\d+)/qty')[0]
            except Exception:
                self.log('Error [%s]' % response.url)
                continue

            price = ''.join(product.select('.//span[(parent::p[not(@class="old-price")] or parent::span[not(@class="weee")]) and contains(@class,"price")]/text()').re(r'([0-9\.\, ]+)')).replace(',', '.').strip()
            sku = product.select('.//p[@class="product-ids" and contains(text(), "Ref")]/text()').re(r'Ref : (.*)')
            image_url = product.select('.//a[@class="product-image"]/img/@src').extract()
            # stock = product.select('.//p[contains(@class, "availability") and contains(@class, "in-stock")]')

            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('identifier', identifier)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('image_url', image_url)
            loader.add_value('url', url)
            loader.add_value('stock', 1)

            item = loader.load_item()
            if item.get('sku', '').lower().startswith('spe'):
                yield Request(url, callback=self.parse_sku, meta={'item': item})
            else:
                yield item

    def parse_sku(self, response):
        "Not used for now"
        hxs = HtmlXPathSelector(response)

        item = response.meta.get('item')

        sku = hxs.select('//div[@class="manufacturer"]/p/text()').re(': (.*)')
        sku = sku[0].strip().lower() if sku else []

        if sku:
            item['sku'] = sku

        yield item

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        pages = response.xpath('//div[@class="pages"]//a/@href').extract()
        subcats = response.css('div.souscat a::attr(href)').extract()
        for page in pages:
            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse)

        for subcat in subcats:
            yield Request(urljoin_rfc(get_base_url(response), subcat), callback=self.parse)

        for p in self.parse_category(response):
            yield p

    def closing_parse_simple(self, response):
        for item in super(MaxoutilSpider, self).closing_parse_simple(response):
            if not item['identifier'] in self.identifiers_collected:
                self.identifiers_collected.add(item['identifier'])
                yield item
