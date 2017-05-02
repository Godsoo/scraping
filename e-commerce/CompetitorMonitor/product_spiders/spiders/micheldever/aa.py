import re
import os
import csv
from scrapy import Request, signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.items import Product, ProductLoader
from product_spiders.spiders.micheldever.eventtyres_spider import EvenTyresSpider
from product_spiders.lib.schema import SpiderSchema
from micheldeverutils import find_mts_stock_code


HERE = os.path.dirname(os.path.abspath(__file__))


class TheAASpider(EvenTyresSpider):
    name = 'micheldever-theaa.com'
    allowed_domains = ['theaa.com']

    website_url = 'https://tyres.theaa.com/'
    postal_code = 'CV47 0RB'
    price_discount = True

    theaa_brand_urls = [
        ('Premme', 'https://tyres.theaa.com/manufacturer/premme/'),
    ]

    def __init__(self, *args, **kwargs):
        super(TheAASpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        # It first crawls the EAN codes from manufacturer's page
        # In spider_idle method it'll set main_crawl to True and parse the products
        self.main_crawl = False

        # Parse brands
        self.theaa_should_parse_brand = True

        self.ean_codes = {}
        self.ean_codes_filename = os.path.join(HERE, 'theaa_ean_codes.csv')
        if os.path.exists(self.ean_codes_filename):
            with open(self.ean_codes_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.ean_codes[row['identifier']] = row['ean_code']

    def spider_idle(self, spider):
        if not self.main_crawl:
            self.main_crawl = True
            for req in list(super(TheAASpider, self).start_requests()):
                self.crawler.engine.crawl(req, self)
        elif self.theaa_should_parse_brand:
            self.theaa_should_parse_brand = False
            for brand, url in self.theaa_brand_urls:
                req = Request(url, meta={'brand': brand},
                              callback=self.theaa_parse_brand,
                              dont_filter=True)
                self.crawler.engine.crawl(req, self)

    def spider_closed(self, spider):
        with open(self.ean_codes_filename, 'w') as f:
            writer = csv.DictWriter(f, ['identifier', 'ean_code'])
            writer.writeheader()
            for identifier, ean_code in self.ean_codes.iteritems():
                new_row = {'identifier': identifier, 'ean_code': ean_code}
                writer.writerow(new_row)

    # @Override
    # This spider extracts EAN codes which are used for Automatch
    def start_requests(self):
        yield Request('https://tyres.theaa.com/manufacturers/',
                      callback=self.theaa_parse_manufacturers)

    # @Override
    # Add auto matching by EAN code
    def find_mts_stock_code(self, product):
        ean_code = self.ean_codes.get(product['identifier'])
        if ean_code:
            product['sku'] = ean_code
        return find_mts_stock_code(product, spider_name=self.name, log=self.log, ean_code=ean_code)

    def theaa_parse_manufacturers(self, response):
        schema = SpiderSchema(response)
        brands = filter(lambda i: i['type'] == 'http://schema.org/Brand', schema.data['items'])
        for brand in brands:
            yield Request(brand['properties']['url'], callback=self.theaa_parse_products)

    def theaa_parse_products(self, response):
        schema = SpiderSchema(response)
        for p in schema.get_products():
            yield Request(p['url'], callback=self.theaa_parse_ean)

    def theaa_parse_ean(self, response):
        products = response.xpath('//*[@itemtype="http://schema.org/Product"]')
        for product_xs in products:
            pid = product_xs.xpath('@data-id').extract_first()
            if not pid:
                continue
            id_name = ' '.join(product_xs.xpath('.//*[@itemprop="name"]/text()').extract_first().strip().split()).upper()
            ean = product_xs.xpath('@data-gtin').extract_first()
            if ean and (id_name not in self.ean_codes):
                self.ean_codes[id_name] = ean

    def theaa_parse_brand(self, response):
        schema = SpiderSchema(response)
        for p in schema.get_products():
            response.meta['product_name'] = p['name']
            yield Request(p['url'], meta=response.meta,
                          callback=self.theaa_parse_all_products,
                          dont_filter=True)

    def theaa_parse_all_products(self, response):
        products = response.xpath('//*[@itemtype="http://schema.org/Product"]')
        for product_xs in products:
            pid = product_xs.xpath('@data-id').extract_first()
            if not pid:
                continue
            id_name = ' '.join(product_xs.xpath('.//*[@itemprop="name"]/text()').extract_first().strip().split()).upper()
            width, aspect_ratio, rim, load_rating, speed_rating = re.search(r'(\d+)/(\d+)R(\d+)\s(\d+)(\w)', id_name).groups()
            is_xl = bool(product_xs.xpath('.//*[@data-icon="XL"]'))
            is_rf = bool(product_xs.xpath('.//*[@data-icon="RF"]'))
            images = response.css('.single__graphics').xpath('./img/@src').extract()
            ean = product_xs.xpath('@data-gtin').extract_first()
            price = product_xs.xpath('.//*[@itemprop="price"]/text()').extract_first()
            fuel, grip, noise = product_xs.css('.product__meta-list').xpath('li/text()').extract()

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', ean)
            loader.add_value('sku', ean)
            loader.add_value('name', response.meta['product_name'])
            loader.add_value('price', price)
            loader.add_value('url', response.url)
            loader.add_value('brand', response.meta['brand'])
            if images:
                loader.add_value('image_url', response.urljoin(images[-1]))
            item = loader.load_item()
            item['metadata'] = {
                'full_tyre_size': '%s/%s/%s/%s/%s' % (width, aspect_ratio, rim, load_rating, speed_rating),
                'width': width,
                'aspect_ratio': aspect_ratio,
                'rim': rim,
                'load_rating': load_rating,
                'speed_rating': speed_rating,
                'xl': 'Yes' if is_xl else 'No',
                'run_flat': 'Yes' if is_rf else 'No',
                'grip': grip, 'fuel': fuel, 'noise': noise,
            }

            yield item

    def get_identifier(self, selector):
        brand = selector.xpath('.//*[@itemprop="brand"]//*[@itemprop="name"]/text()').extract()[0].strip()
        full_name = selector.xpath('.//*[contains(@class, "product__title") and @itemprop="name"]/text()').extract()[0]
        id_name = ' '.join(map(unicode.strip, re.split(brand, full_name, flags=re.I)))
        return id_name
