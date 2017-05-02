import os
import time
import re
import urllib
import csv
from datetime import datetime
from w3lib.url import add_or_replace_parameter
from scrapy import Spider, Selector, Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


def multiply(lst):
    if not lst:
        return []

    while len(lst) > 1:
        if len(lst[0]) > 1000:
            return []

        result = []
        for name0 in lst[0]:
            for name1 in lst[1]:
                result.append(name0 + '@' + name1)
        lst = [result] + lst[2:]
    # Dynamic list
    if not lst[0]:
        return []
    return lst[0]


HERE = os.path.dirname(os.path.abspath(__file__))


class TweekscyclesSpider(Spider):
    name = 'tweekscycles-tweekscycles.com'
    allowed_domains = ['tweekscycles.com']
    start_urls = ['http://www.tweekscycles.com/']

    def __init__(self, *args, **kwargs):
        super(TweekscyclesSpider, self).__init__(*args, **kwargs)
        self.currency_set = False
        self.vat_set = False
        self.skus = set()
        self.categories = dict()

        with open(os.path.join(HERE, 'tweekscycles_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.skus.add(row['Code'])
                
        with open(os.path.join(HERE, 'tweekscycles_categories.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.categories[row['Code']] = [x for x in (row['Category'], row['Sub Category']) if x]

    def preprocess_product(self, item):
        if item['identifier'] in self.skus:
            item['category'] = ' > '.join(self.categories.get(item['identifier'], [item['category']]))
            return item
        return None

    def start_requests(self):
        yield Request('http://tweekscycles.com', callback=self.parse_options)

    def parse_options(self, response):
        if not self.currency_set:
            self.currency_set = True
            yield Request('http://www.tweekscycles.com/Currency.do?c=4&uid={}'.format(int(time.time())), callback=self.parse_options, dont_filter=True)
            return
        if not self.vat_set:
            self.vat_set = True
            yield Request('http://www.tweekscycles.com/Vat.do?v=INC&uid={}'.format(int(time.time())), callback=self.parse_options, dont_filter=True)
            return

        yield Request('http://www.tweekscycles.com/sitemap', dont_filter=True)

    def parse(self, response):
        cats = response.xpath('//div[@id="title"]//a/@href').extract()
        cats += response.xpath('//div[starts-with(@id,"menu-")]//a/@href').extract()
        cats += response.xpath('//div[@id="content"]//a/@href').extract()
        # cats = ['http://www.tweekscycles.com/cycling-clothing/mountain-bike-helmets']
        for cat in cats:
            yield Request(response.urljoin(cat), callback=self.parse_cat)

    def parse_cat(self, response):
        m = re.search(r'showAllItems\(\\"(.*)\\"\)', response.body)
        if m:
            yield Request('http://www.tweekscycles.com/Summary.do?method=changeShowAll&a=1&n=%s&uid=%s' % (m.group(1), datetime.now().strftime("%s000")), callback=self.parse_catall)
            yield Request ('http://www.tweekscycles.com/Summary.do?method=changePage&p=1&o=1&n=%s&uid=%s' % (m.group(1), datetime.now().strftime("%s000")), callback=self.parse_catall)

        for prod in response.xpath('//td[@valign="middle" or @valign="top"]//a/@href').extract():
            yield Request(response.urljoin(prod), callback=self.parse_product)

    def parse_catall(self, response):
        error = False
        try:
            html = response.body.split('@@ebusiness@@')[1]
        except:
            error = True
        if error:
            req = response.request
            meta = response.meta
            retries = meta.get('retries', 0)
            if retries < 3:
                meta['retries'] = retries + 1
                self.log('Retrying {}, attempt: {}'.format(req.url, retries + 1))
                yield req.replace(dont_filter=True, callback=self.parse_catall, meta=meta)
            return
        hxs = Selector(text=html)
        for prod in hxs.xpath('//td[@valign="middle" or @valign="top"]//a/@href').extract():
            yield Request(response.urljoin(prod), callback=self.parse_product)

        pagination = response.body.split('@@ebusiness@@')[0]
        if not pagination:
            return
        pages = re.findall(r"changePage\('(.+?)',", pagination)
        for page in pages:
            url = add_or_replace_parameter(response.url, 'p', page)
            yield Request(url, self.parse_catall)

    def parse_product(self, response):
        # This looses part of HTML on http://www.tweekscycles.com/clearance/clearance-bikes/scott-scale-935-29er-hardtail-mountain-bike-2014
        # No idea why and how but response.xpath('//select') finds only one elem
        # while the same with text=response.body finds them all
        hxs = Selector(text=response.body.decode('ISO-8859-1'))

        if not hxs.xpath('//td[@id="product-title"]'):
            # nope, category
            for x in self.parse_cat(response):
                if isinstance(x, Product):
                    yield self.preprocess_product(x)
                else:
                    yield x
            return

        category = ''.join(hxs.xpath('normalize-space(//div[@id="breadcrumb"]/a[position()=last()]/text())').extract())
        brand = ''.join(hxs.xpath('//td[@id="brand-location"]/img/@alt').extract())
        img = hxs.xpath('//img[@id="mainImage"]/@src').extract()
        img = response.urljoin(img[0]) if img else ''
        url = response.url
        shipping_cost = '0'

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('shipping_cost', shipping_cost)
        loader.add_value('brand', brand)
        loader.add_value('url', url)
        loader.add_value('category', category)
        loader.add_value('image_url', img)

        opts = []

        req = hxs.xpath('//div[@id="attribOption"]//select[@onchange]/@onchange').extract()
        self.log(repr(req))
        if req:
            m = re.search("updateAttrib\('(.*)', '(.*)', '(.*)'\)", req[0])
            n, g = m.group(1), m.group(2)
            i = hxs.xpath('//input[@name="iid"]/@value').extract().pop()
            for sel in hxs.xpath('//div[@id="attribOption"]//select[@onchange]'):
                group = []
                for opt in sel.select('./option[position()!=1]/@value').extract():
                    group.append(opt)
                opts.append(group)

            for opt in multiply(opts):
                url = 'http://www.tweekscycles.com/Product.do?method=prodAttrib&n=%s&g=%s&a=%s&i=%s&q=1&uid=%s'
                try:
                    yield Request(url % (n, g, urllib.quote_plus(opt+'@'), i, datetime.now().strftime("%s000")),
                                  meta={'item': loader.load_item()}, callback=self.parse_opt)
                except KeyError:
                    pass
        else:
            options = hxs.xpath("//div[@id='buyButton']/parent::td/parent::tr")
            if options:
                for option in options:
                    name = hxs.xpath("//td[@id='product-title']/text()").extract()[0].strip()
                    name = name + ' - ' + option.select("./td[1]/text()").extract()[0].strip()
                    price = option.select("./td[3]/span/text()").extract()[0].strip()
                    price = extract_price(price)
                    stock = 1 if price > 0 else 0
                    identifier = option.select(".//div[@id='buyButton']").extract()[0]
                    identifier = re.findall(re.compile("addExpandBasket\(.+?\'(\d*)\'\)"), identifier)

                    loader = ProductLoader(item=Product(), selector=hxs)
                    loader.add_value('shipping_cost', shipping_cost)
                    loader.add_value('brand', brand)
                    loader.add_value('url', url)
                    loader.add_value('category', category)
                    loader.add_value('image_url', img)
                    loader.add_value('name', name)
                    loader.add_value('identifier', identifier)
                    loader.add_value('sku', identifier)
                    loader.add_value('price', str(price))
                    loader.add_value('stock', stock)
                    yield self.preprocess_product(loader.load_item())
            else:
                loader.add_xpath('name', 'normalize-space(//td[@id="product-title"]/text())')
                loader.add_xpath('sku', 'normalize-space(//span[@id="prodTitle"]/span[position()=last()]/text())')
                loader.add_xpath('identifier', 'normalize-space(//span[@id="prodTitle"]/span[position()=last()]/text())')
                if not loader.get_output_value('identifier'):
                    loader.add_value('identifier', re.search("review\('[^']*', '0', '([^']*)'\)", response.body).group(1))
                loader.add_xpath('price', '//span[@id="prodPriceLower" or @id="prodPrice"]/span/text()')
                if loader.get_output_value('price') > 0:
                    loader.add_value('stock', '1')

                yield self.preprocess_product(loader.load_item())

    def parse_opt(self, response):
        item = response.meta['item']
        if not u'@@ebusiness@@' in response.body:
            self.log('@@ebusiness@@ not in {}'.format(response.url))
            req = response.request
            meta = response.meta
            retries = meta.get('retries', 0)
            if retries < 3:
                meta['retries'] = retries + 1
                self.log('Retriying {}, attempt: {}'.format(req.url, retries + 1))
                yield req.replace(dont_filter=True, callback=self.parse_opt, meta=meta)
            return
        data = response.body.decode('ISO-8859-1').split('@@ebusiness@@')
        if not data[4]:
            # No such combination
            return

        item['name'] = data[3].replace('&nbsp;&gt;&nbsp;', '')
        try:
            item['price'] = extract_price(data[5].split('&pound;')[1])
        except IndexError:
            item['price'] = 0
        if item['price'] == 0:
            item['stock'] = '0'
        else:
            item['stock'] = '1'
        item['sku'] = data[4].split('>')[-2].split('<')[0]
        item['identifier'] = data[4].split('>')[-2].split('<')[0]

        yield self.preprocess_product(item)
