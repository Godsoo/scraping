import os
import re
import csv
import itertools
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

from uberkidsitems import UberKidsMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class UberKidsSpider(BaseSpider):
    name = 'uberkids-uberkids.co.uk'

    filename = os.path.join(HERE, 'uberkids_products_search.csv')
    categories_filename = os.path.join(HERE, 'UberKids-CompetitorMonitorCategory.csv')
    start_urls = ('http://www.uberkids.co.uk',)

    rows = {}

    def start_requests(self):
        with open(self.filename) as f:    
            reader = csv.DictReader(f)
            for row in reader:
                self.rows[row['Code'].strip().upper()] = row
        
        self.categories = dict()
        with open(self.categories_filename) as f:    
            reader = csv.DictReader(f)
            for row in reader: 
                self.categories[row['Code'].strip().upper()] = (row['Category'], row['Sub Category'])
                
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        categories = response.xpath('//div[@id="header"]//div[contains(@id, "button")]//a/@href').extract()
        categories += response.xpath('//div[@id="left-menu"]//a[not(contains(@href, "javascript"))]/@href').extract()
        categories += response.xpath('//div[@id="content"]//table/tr/td//a[@class="stdBold"]/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        category_id = response.xpath('//body/@onload').re("initSummary\('(\d+)'")
        if category_id:
            category = 'http://www.uberkids.co.uk/Summary.do?method=changeShowAll&a=1&n=' + category_id[0]
            yield Request(category)

        products = response.xpath('//td/a[@class="std"]/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

    def parse_product(self, response):
        name = response.xpath('//td[@id="product-title"]/text()').extract()[0].strip()
        categories = map(lambda x: x.strip(), response.xpath('//div[@id="breadcrumb"]/a/text()').extract())[1:]
        price = response.xpath('//span[@id="prodPrice"]/span/text()').extract()
        price = price[0] if price else '0'
        image_url = response.xpath('//a[@id="mainEnlargeImage"]/@href').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''
        brand = response.xpath('//td[@id="brand-location"]/img/@alt').extract()
        brand = brand[0].strip() if brand else ''
        sku = response.xpath('//span[@id="prodTitle"]/span/text()').extract()
        sku = sku[-1].strip() if sku else ''


        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', sku)
        loader.add_value('sku', sku)
        loader.add_value('brand', brand)
        loader.add_value('category', categories)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('image_url', image_url)
        loader.add_value('url', response.url)
        item = loader.load_item()

        metadata = UberKidsMeta()
        metadata['mpn'] = item['sku'][3:] if item.get('sku', None) else ''
        item['metadata'] = metadata

        options = response.xpath('//select[contains(@onchange, "updateAttrib")]')
        if options:
            option_url = "http://www.uberkids.co.uk/Product.do?method=prodAttrib&n=%s&g=%s&a=%s@&q=1"
            option_elements = []
            for option in options:
                option_elements.append(option.xpath('option[@value!="select"]/@value').extract())
            
            option_combinations = list(itertools.product(*option_elements))
            n, g, tmp = options[0].xpath('@onchange').re("\d+")
            for option_combination in option_combinations:
                option_value = '@'.join(option_combination)
                meta = response.meta
                meta['item'] = deepcopy(item)
                yield Request(option_url % (n, g, option_value), dont_filter=True, callback=self.parse_options, meta=meta)
        else:
            product_found = self.rows.get(sku)
            if product_found:
                categories = self.categories.get(sku.upper())
                item['category'] = ' > '.join([s for s in categories if s])
                yield item

    def parse_options(self, response):
        item = response.meta['item']

        option_data = response.body.split('@@@@')

        identifier = option_data[0]
        image_url = option_data[1]

        product_data = response.xpath('//span/text()').extract()
        if len(product_data)<3:
            sku, price = response.xpath('//span/text()').extract()
            name = ''
        else:
            name, sku, price = response.xpath('//span/text()').extract()[:3]
        
        # Some products doesn't show name, so the sku goes to name variable
        product_found = self.rows.get(name, None)
        if product_found:
            sku = name
            name = ''
        else:
            product_found = self.rows.get(sku, None)

        if product_found:
            item['identifier'] = sku
            item['sku'] = sku
            item['metadata']['mpn'] = sku[3:]
            if image_url.endswith('.jpg'):
                item['image_url'] = response.urljoin(image_url)
            if name:
                item['name'] += ' '+ name
            item['price'] = extract_price(price)
            categories = self.categories.get(sku.upper())
            item['category'] = ' > '.join([s for s in categories if s])            
            yield item
    
