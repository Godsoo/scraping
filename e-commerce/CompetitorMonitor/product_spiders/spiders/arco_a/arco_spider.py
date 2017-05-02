import re
import csv
import os
import json

from scrapy import Spider, Request
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class ArcoSpider(Spider):
    name = 'arco_a_arco.co.uk'
    allowed_domains = ['arco.co.uk']

    start_urls = ('http://arco.co.uk', )

    pages_url = 'http://www.arco.co.uk/productlistisland?\
view=gallery&pi_sn=true&si=%(si)s&rpp=%(rpp)s&pcatid=%(pcatid)s&\
pi_includeRecentAfterBottomNav=true'

    search_url = 'http://www.arco.co.uk/textsearch?event=textsearch&fromsearch=x&searchTerms=%(sku)s&eSearch=Products'

    pcatid_regex = re.compile(".*\?.*pcatid=([^&]*)")

    category = 'a'

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        kwargs['_crawler'] = crawler
        return cls(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        super(ArcoSpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.spider_idle, signals.spider_idle)
        if kwargs.get('_crawler'):
            self._crawler = kwargs['_crawler']

        self.products = {}
        self.deletions = []
        self.found_products = []
        self.tries = {}
        self.max_tries = 10
        self.category_requests = []
        self.page_requests = []
        self.product_requests = []

        self.processed_urls = set()

        self.log("Category: %s" % self.category)


        with open(os.path.join(HERE, 'arco_deletions.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['account'].strip().lower() == self.category.lower():
                    self.deletions.append(row['product'])


        with open(os.path.join(HERE, 'arco_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['category'].strip().lower() == self.category.lower() and row['product'].strip() not in self.deletions:
                    p = {
                        'category': row['category'].strip(),
                        'product': row['product'].strip(),
                        'description': row['description'].strip().decode('utf'),
                        'group': row['group'].strip(),
                        'brand': row['brand'].strip(),
                        'price': row['price'].strip(),
                        'price_uom': row['price_uom'].strip(),
                        'price_per': row['price_per'].strip()
                    }
                    self.products[p['product']] = p

        with open(os.path.join(HERE, 'arco_additions.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['account'].strip().lower() == self.category.lower():
                    p = {
                        'mandatory': True,
                        'category': '',
                        'product': row['product'].strip(),
                        'description': row['description'].strip().decode('utf'),
                        'group': '',
                        'brand': row['brand'].strip(),
                        'price': '',
                        'price_uom': '',
                        'price_per': ''
                    }
                    self.products[p['product']] = p

    def start_requests(self):
        for sku, product in self.products.items():
            url = self.search_url % {'sku': sku}
            r = Request(url, callback=self.parse_product2, meta={'product': product})
            yield r
            break

    def _invoke_next_req(self):
        res = None
        for sku, product in self.products.items():
            if sku not in self.found_products:
                if sku in self.tries and self.tries[sku] <= self.max_tries:
                    url = self.search_url % {'sku': sku}
                    res = Request(url, callback=self.parse_product2, dont_filter=True, meta={'product': product})
                    break
        return res

    def spider_idle(self, spider):
        self.log("SPIDER IDLE")

        request = None
        for sku, product in self.products.items():
            if sku not in self.found_products:
                if (sku in self.tries and self.tries[sku] <= self.max_tries) or (sku not in self.tries):
                    url = self.search_url % {'sku': sku}
                    request = Request(url, callback=self.parse_product2, dont_filter=True, meta={'product': product})
                    break

        if request:
            self._crawler.engine.crawl(request, self)
        else:
            self.log("Number of found products: %d" % len(self.found_products))
            self.log("SKUs not found: %s" % [sku for sku in self.products if sku not in self.found_products])

    def parse_product2(self, response):
        found = False
        product = response.meta['product']
        sku = product['product']
        if not sku in self.tries:
            self.tries[sku] = 1
        else:
            self.tries[sku] += 1

        image_url = response.xpath(u'//div[@id="imageholder"]//img[@name="lpic"]/@src')
        if not image_url:
            image_url = response.xpath("//div[@id='productImage']/img/@src")
        if image_url:
            image_url = image_url[0].extract()
            image_url = response.urljoin(image_url)
        else:
            image_url = ''

        options = response.xpath(u'//table[@class="producttbl"]//tr[not(child::th)]')
        for option in options:
            if not option.xpath(u'./td[2]/span[@class="linedesc"]'):
                continue
            sku = option.xpath(u'./td[1]/text()')[0].extract().strip()
            if sku in self.products:
                self.found_products.append(sku)
                product = self.products[sku]
                brand = product['brand']
                name = product['description']
                price = option.xpath(u'./td[4]/div/text()')[0].extract()
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('category', product['group'])
                loader.add_value('name', name)
                loader.add_value('brand', brand)
                loader.add_value('url', response.url)
                loader.add_value('price', price)
                loader.add_value('image_url', image_url)
                loader.add_value('sku', sku)
                loader.add_value('identifier', sku)
                found = True
                yield loader.load_item()
        if not options:
            m = re.search('skus =\s*(\{[^;]*});', response.body, re.M)
            if m:
                options_js = m.group(1).replace("'", '"')
                options = json.loads(options_js)

                def parse(options, name=''):
                    if not isinstance(options, dict):
                        return None
                    if 'code' in options:
                        res = options.copy()
                        res['name'] = name
                        return res
                    res = []
                    for key, value in options.items():
                        name_part = name + ' ' + key
                        subres = parse(value, name_part)
                        if isinstance(subres, list):
                            res += subres
                        else:
                            res.append(subres)
                    return res

                name = response.xpath("//div[@id='productDesc']/h1/text()").extract()[0]

                products = parse(options, name=name)
                for p in products:
                    sku = p['code']
                    if sku in self.products:
                        self.found_products.append(sku)
                        product = self.products[sku]
                        brand = product['brand']
                        #name = p['name']
                        name = product['description']
                        #category = product['group']
                        # if not brand.lower() in name.lower():
                        # name = u'%s %s' % (brand, name)
                        price = p['price']
                        loader = ProductLoader(item=Product(), response=response)
                        loader.add_value('category', product['group'])
                        loader.add_value('name', name)
                        loader.add_value('brand', brand)
                        loader.add_value('url', response.url)
                        loader.add_value('price', price)
                        loader.add_value('image_url', image_url)
                        loader.add_value('sku', sku)
                        loader.add_value('identifier', sku)
                        found = True
                        yield loader.load_item()

        if not found and product.get('mandatory', False):
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', sku)
            loader.add_value('sku', sku)
            loader.add_value('name', product['description'])
            loader.add_value('brand', product['brand'])
            loader.add_value('price', 0)
            yield loader.load_item()

        yield self._invoke_next_req()
