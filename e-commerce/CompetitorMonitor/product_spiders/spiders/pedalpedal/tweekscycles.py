import time
import re
import urllib
from datetime import datetime
from w3lib.url import add_or_replace_parameter
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from product_spiders.base_spiders.primary_spider import PrimarySpider

from crcitem import CRCMeta

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


class TweeksSpider(PrimarySpider):
    name = 'tweekscycles.com'
    allowed_domains = ['tweekscycles.com']
    start_urls = ['http://www.tweekscycles.com/']

    csv_file = 'tweekscycles_products.csv'
    json_file = 'tweekscycles_metadata.json'

    def __init__(self, *args, **kwargs):
        super(TweeksSpider, self).__init__(*args, **kwargs)
        self.currency_set = False
        self.vat_set = False

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
    
        yield Request('http://www.tweekscycles.com', dont_filter=True)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        cats = hxs.select('//div[@id="title"]//a/@href').extract()
        cats += hxs.select('//div[starts-with(@id,"menu-")]//a/@href').extract()
        for cat in cats:
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        m = re.search(r'showAllItems\(\\"(.*)\\"\)', response.body)
        if m:
            yield Request('http://www.tweekscycles.com/Summary.do?method=changeShowAll&a=1&n=%s&uid=%s' % (m.group(1), datetime.now().strftime("%s000")), callback=self.parse_catall)
            yield Request ('http://www.tweekscycles.com/Summary.do?method=changePage&p=1&o=1&n=%s&uid=%s' % (m.group(1), datetime.now().strftime("%s000")), callback=self.parse_catall)
        
        for prod in hxs.select('//td[@valign="middle" or @valign="top"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), prod), callback=self.parse_product)

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
        hxs = HtmlXPathSelector(text=html)
        for prod in hxs.select('//td[@valign="middle" or @valign="top"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), prod), callback=self.parse_product)
            
        pagination = response.body.split('@@ebusiness@@')[0]
        if not pagination:
            return
        pages = re.findall(r"changePage\('(.+?)',", pagination)
        for page in pages:
            url = add_or_replace_parameter(response.url, 'p', page)
            yield Request(url, self.parse_catall)

    def parse_product(self, response):
        # This looses part of HTML on http://www.tweekscycles.com/clearance/clearance-bikes/scott-scale-935-29er-hardtail-mountain-bike-2014
        # No idea why and how but hxs.select('//select') finds only one elem
        # while the same with text=response.body finds them all
        hxs = HtmlXPathSelector(text=response.body.decode('ISO-8859-1'))

        if not hxs.select('//td[@id="product-title"]'):
            # nope, category
            for x in self.parse_cat(response):
                yield x
            return

        category = ''.join(hxs.select('normalize-space(//div[@id="breadcrumb"]/a[position()=last()]/text())').extract())
        brand = ''.join(hxs.select('//td[@id="brand-location"]/img/@alt').extract())
        img = hxs.select('//img[@id="mainImage"]/@src').extract()
        img = urljoin_rfc(get_base_url(response), img[0]) if img else ''
        url = response.url
        shipping_cost = '0'

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('shipping_cost', shipping_cost)
        loader.add_value('brand', brand)
        loader.add_value('url', url)
        loader.add_value('category', category)
        loader.add_value('image_url', img)

        opts = []

        req = hxs.select('//div[@id="attribOption"]//select[@onchange]/@onchange').extract()
        self.log(repr(req))
        if req:
            m = re.search("updateAttrib\('(.*)', '(.*)', '(.*)'\)", req[0])
            n, g = m.group(1), m.group(2)
            i = hxs.select('//input[@name="iid"]/@value').extract().pop()
            for sel in hxs.select('//div[@id="attribOption"]//select[@onchange]'):
                group = []
                for opt in sel.select('./option[position()!=1]/@value').extract():
                    group.append(opt)
                opts.append(group)

            for opt in multiply(opts):
                url = 'http://www.tweekscycles.com/Product.do?method=prodAttrib&n=%s&g=%s&a=%s&i=%s&q=1&uid=%s'
                try:
                    yield Request(url % (n, g, urllib.quote_plus(opt+'@'), i, datetime.now().strftime("%s000")),
                        meta={'item':loader.load_item()}, callback=self.parse_opt)
                except KeyError:
                    pass
        else:
            options = hxs.select("//div[@id='buyButton']/parent::td/parent::tr")
            if options:
                for option in options:
                    name = hxs.select("//td[@id='product-title']/text()").extract()[0].strip()
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
                    yield loader.load_item()
            else:
                loader.add_xpath('name', 'normalize-space(//td[@id="product-title"]/text())')
                loader.add_xpath('sku', 'normalize-space(//span[@id="prodTitle"]/span[position()=last()]/text())')
                loader.add_xpath('identifier', 'normalize-space(//span[@id="prodTitle"]/span[position()=last()]/text())')
                if not loader.get_output_value('identifier'):
                    loader.add_value('identifier', re.search("review\('[^']*', '0', '([^']*)'\)", response.body).group(1))
                loader.add_xpath('price', '//span[@id="prodPriceLower" or @id="prodPrice"]/span/text()')
                if loader.get_output_value('price') > 0:
                    loader.add_value('stock', '1')
                rrp = hxs.select('//span[@id="prodPrice"]/span/text()').re(r'Was (.*)')
                rrp = str(extract_price(rrp[-1])) if rrp else ''

                prod = loader.load_item()
                metadata = CRCMeta()
                metadata['rrp'] = rrp
                prod['metadata'] = metadata
                yield prod

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

        try:
            rrp = re.search(r'Was &pound;(.*)<br', data[5]).group(1)
        except AttributeError:
            rrp = ''

        metadata = CRCMeta()
        metadata['rrp'] = rrp
        item['metadata'] = metadata

        yield item
