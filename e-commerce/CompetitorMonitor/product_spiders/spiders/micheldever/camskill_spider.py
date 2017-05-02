import os
import csv
import json

from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoader
from micheldeveritems import MicheldeverMeta
from micheldeverutils import (
    find_mts_stock_code,
    is_product_correct,
)


HERE = os.path.abspath(os.path.dirname(__file__))


class CamSkillSpider(Spider):
    name = 'micheldever-camskill.co.uk'
    allowed_domains = ['camskill.co.uk']
    rotate_agent = True
    start_urls = ('http://www.camskill.co.uk/products.php',)

    def __init__(self, *argv, **kwgs):
        super(CamSkillSpider, self).__init__(*argv, **kwgs)

        self.products_data = {}
        with open(os.path.join(HERE, 'camskill.json-lines')) as f:
            for l in f:
                if l:
                    data = json.loads(l)
                    self.products_data[data['identifier']] = data

        fname_ids = os.path.join(HERE, 'camskill_incorrect.csv')
        if os.path.exists(fname_ids):
            with open(fname_ids) as f:
                reader = csv.reader(f)
                for row in reader:
                    if row[0] in self.products_data:
                        del self.products_data[row[0]]

    def parse(self, response):
        links = response.xpath('//div[@class="masterCategoryDetail"]/h2/a[not(contains(text(), "Winter"))]/@href').extract()
        links += response.xpath('//h2/following-sibling::strong/a/@href').extract()
        for url in links:
            yield Request(response.urljoin(url))

        if not links:
            for item in self.parse_products(response):
                yield item

    def parse_products(self, response):
        products = response.xpath('//div[@id="productListings"]/article')
        self.log('{} products found'.format(len(products)))
        for product in products:
            try:
                identifier = product.xpath('.//div[@class="productListingPrice"]/a/@href').re(r'/m.*p(\d+)/')[0]
                price = product.xpath('.//section[@class="pricing"]/*/text()').re(r'[\d\.,]+')[0]
            except:
                continue
            product_data = self.products_data.get(identifier)
            if not product_data:
                continue

            loader = ProductLoader(item=Product(), selector=product)
            for field in ['identifier', 'name', 'url', 'image_url', 'category', 'brand']:
                loader.add_value(field, product_data.get(field) or '')

            loader.add_value('price', price)

            item = loader.load_item()
            metadata = MicheldeverMeta()
            for m in product_data['metadata']:
                metadata[m] = product_data['metadata'][m]
            item['metadata'] = metadata

            if not is_product_correct(item):
                continue

            item['metadata']['mts_stock_code'] = find_mts_stock_code(item, spider_name=self.name, log=self.log)

            yield item
