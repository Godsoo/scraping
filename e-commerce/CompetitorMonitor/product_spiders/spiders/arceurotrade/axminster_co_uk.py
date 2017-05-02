import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class AxminsterCoUkSpider(BaseSpider):
    name = 'axminster.co.uk'
    allowed_domains = ['axminster.co.uk']

    def __init__(self, *args, **kwargs):
        super(AxminsterCoUkSpider, self).__init__(*args, **kwargs)
 
    def start_requests(self):
        yield Request('http://axminster.co.uk/', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@id="holder_NAVIGATION"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@id="productDataOnPage"]//h3/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

        for url in hxs.select(u'//div[@class="subcatHOLDER"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

        for url in hxs.select(u'//div[@class="catFILTERS_b"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1/text()')
        # inc. vat
        product_loader.add_xpath('price', u'//span[@class="price"]/text()')
        product_loader.add_xpath('category', u'//div[@id="crumb"]/a[2]/text()')

        img = hxs.select(u'//img[@id="productImage"]/@src').extract()[0]
        product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img))

        product_loader.add_xpath('sku', u'//span[@id="divskucode1"]/text()')
        product_loader.add_xpath('identifier', u'//span[@id="divskucode1"]/text()')
        product_loader.add_xpath('sku', u'//input[@name="pf_id"]/@value')
        product_loader.add_xpath('identifier', u'//input[@name="pf_id"]/@value')
        product_loader.add_xpath('brand', 'substring-after(//div[@class="brandlogo"]/a/img/@alt, "View All Products From ")')
#product_loader.add_xpath('shipping_cost', '')

        options = []
        for line in response.body.split('\n'):
            if 'new seldata(' in line:
                parts = line.split('new seldata(')[1:]
                for part in parts:
                    part = part.split(');')[0].replace('new Array', '').replace(')', ',)')
                    try:
                        data = eval('(' + part + ')')
                    except:
                        # no options
                        break
                    self.log(part)
                    options.append((data[0], data[2], data[-2]))

        product = product_loader.load_item() 
        if 'price' not in  product:
            product['price'] = None

        if options:
            for opt in options:
                prod = Product(product)
                prod['name'] = prod['name'] + ' ' + ' '.join(opt[0])
                prod['sku'] = opt[1]
                prod['price'] = Decimal(opt[2].split('price=')[1].split('&')[0].replace(',',''))
                prod['identifier'] = opt[1]
                yield prod
        # http://www.axminster.co.uk/axminster-veritas-additional-mounting-plates-with-rod-for-veritas-carvers-vice-prod821439/
        elif hxs.select('//div[@class="prodOPTIONS"]'):
            for opt in hxs.select('//div[@class="prodOPTIONS"]'):
                prod = Product(product)
                prod['name'] = prod['name'] + ' ' + opt.select(u'normalize-space(.//div[@class="option"]/text())').extract()[0]
                prod['sku'] = opt.select(u'.//input[@name="sku"]/@value').extract()[0]
                prod['identifier'] = opt.select(u'.//input[@name="sku"]/@value').extract()[0]
                prod['price'] = extract_price(opt.select(u'.//span[@class="price"]/text()').extract()[0])
                yield prod
        else:
            yield product
