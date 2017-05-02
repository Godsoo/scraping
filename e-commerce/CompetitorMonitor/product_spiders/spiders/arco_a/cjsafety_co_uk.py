import re
import os
import csv
import copy
import itertools
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from product_spiders.base_spiders.primary_spider import PrimarySpider
from product_spiders.config import DATA_DIR


HERE = os.path.abspath(os.path.dirname(__file__))


class CjsafetyCoUkSpider(PrimarySpider):
    name = 'cjsafety.co.uk'
    allowed_domains = ['cjsafety.co.uk']
    start_urls = [
        'http://www.cjsafety.co.uk/',
        ]
    brands = ['B Brand']
    cookie_num = 0

    csv_file = 'cjsafety_crawl.csv'

    def _start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            with open(os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    meta = {
                        'category': row['category'],
                        'brand': row['brand'],
                    }
                    yield Request(row['url'], callback=self.parse_product, meta=meta)
        yield Request(self.start_urls[0], dont_filter=True)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        self.brands = hxs.select('//li[@id and a[contains(text(),"Search Brands")]]/div/ul/li/a/text()').extract()
        cls = [' Footwear', ' Workwear', ' Clothing', ' Safety',
            ' Rainwear', ' Range', ' Products']
        for i in range(len(self.brands)):
            s = self.brands[i]
            for c in cls:
                s = s.replace(c, '')
            self.brands[i] = s

        for url in hxs.select('//li[a[@class="nav-top-link" and contains(text(), "Search Categories")]]/div//a/@href').extract():
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        links = response.xpath('//li[contains(@class, "product-category")]/div/a/@href').extract()
        links += response.xpath('//ul[contains(@class, "product-categories")]//li/a/@href').extract()
        for link in links:
            yield Request(link, callback=self.parse_products_list)

        category = ''
        tmp = hxs.select('//h3[@class="breadcrumb"]/text()').extract()
        if tmp:
            category = re.sub(r' \(Page \d+\)', '' , tmp[0])
        for url in response.xpath('//ul[contains(@class,"products")]/li//a/@href').extract():
            if 'add-to-cart' in url: continue
            yield Request(url, meta={'category':category}, callback=self.parse_product)

        tmp = hxs.select('//ul[@class="page-numbers"]/li/a[contains(@class,"next")]/@href').extract()
        if tmp:
            yield Request(tmp[0], callback=self.parse_products_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_value('category', response.meta.get('category', ''))
        name = ''
        tmp = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        tmp = hxs.select('//*[@itemprop="image"]//@src').extract()
        if tmp:
            loader.add_value('image_url', tmp[0])

        if 'brand' in response.meta:
            loader.add_value('brand', response.meta['brand'])
        else:
            for brand in self.brands:
                if brand.lower() in name.lower():
                    loader.add_value('brand', brand)
                    break
                tmp = hxs.select('//h4/a/text()').extract()
                if tmp and brand.lower() in ' '.join(tmp).lower():
                    loader.add_value('brand', brand)
                    break
                tmp = hxs.select('//span[@class="posted_in"]/a/text()').extract()
                if tmp and brand.lower() in ' '.join(tmp).lower():
                    loader.add_value('brand', brand)
                    break

        tmp = response.xpath('//form[@class="variations_form cart"]/@data-product_id').extract()
        if not tmp:
            tmp = response.xpath('//input[@name="add-to-cart"]/@value').extract()
        if tmp:
            loader.add_value('identifier', tmp[0])
            loader.add_value('sku', tmp[0])
        else:
            for request in self.parse_products_list(response):
                yield request
            return
            

        tmp = hxs.select('//div[@itemprop="offers"]/meta[@itemprop="price"]/@content').extract()
        if tmp:
            price = extract_price(tmp[0])
            loader.add_value('price', price)
            loader.add_value('stock', 1)
        else:
            loader.add_value('stock', 0)

        product = loader.load_item()

        selections = response.xpath('//table[contains(@class, "variations")]//select')
        attrs = []
        for sel in selections:
            attr_name = ''
            tmp = sel.select('@name').extract()
            if tmp:
                attr_name = tmp[0]
            attr_values = []
            for option in sel.select('option'):
                value = ''
                tmp = option.select('@value').extract()
                if tmp:
                    value = tmp[0]
                txt = ''
                tmp = option.select('text()').extract()
                if tmp:
                    txt = tmp[0].strip()
                if value != '':
                    attr_values.append((attr_name, value, txt))
            attrs.append(attr_values)

        attrs = filter(lambda a: a, attrs)

        for option in itertools.product(*attrs):
            item = copy.deepcopy(product)
            item['name'] += ' - ' + '-'.join([attr[2] for attr in option])
            item['identifier'] += '-' + '-'.join([attr[1] for attr in option])
            if item.get('brand', None) and not item['name'].lower().startswith(item['brand'].lower()):
                item['name'] = item['brand'] + ' ' + item['name']
            if item.get('identifier') and item['identifier'].strip():
                yield item
        return
