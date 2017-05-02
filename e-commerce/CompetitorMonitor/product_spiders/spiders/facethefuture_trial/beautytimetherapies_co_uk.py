import re
import json
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class BeautytimetherapiesSpider(BaseSpider):
    name = 'beautytimetherapies.co.uk'
    allowed_domains = ['beautytimetherapies.co.uk']
    start_urls = ['https://www.beautytimetherapies.co.uk/customer/account/login/']

    def _start_requests(self):
        yield Request('http://www.beautytimetherapies.co.uk/skin-accumax.html', callback=self.parse_product)

    def parse(self, response):
        yield FormRequest('https://www.beautytimetherapies.co.uk/customer/account/loginPost/', formdata={'login[username]':'m5l2764k@gmail.com', 'login[password]':'password'}, callback=self.login)

    def login(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//ul[@id="mp-accordion"]/li[position()>1]'):
            cattxt = cat.select('normalize-space(./a/span/text())').extract()[0]
            found = False
            for url in cat.select('./ul//a/@href').extract():
                found = True
                yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list, meta={'category': cattxt})
            if not found:
                yield Request(urljoin_rfc(get_base_url(response), cat.select('./a/@href').extract()[0]), callback=self.parse_list, meta={'category': cattxt})

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//h2[@class="product-name"]/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product, meta=response.meta)

        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list, meta=response.meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('sku', '//input[@name="product"]/@value')
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@class="product-name"]/h1/text()')
        loader.add_xpath('price', '//span[@class="price"]/text()')
        loader.add_value('category', response.meta.get('category'))
        loader.add_value('brand', response.meta.get('category'))

        img = hxs.select('//img[@id="image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        
        if hxs.select('//p[@class="availability in-stock"]'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        loader.add_value('shipping_cost', 0)

        prod = loader.load_item()
        try:
            options = json.loads(re.search('Product.Config\((.*)\);', response.body).group(1))
        except:
            yield prod
            return

        for opt in options['attributes'].values()[0]['options']:
            p = Product(prod)
            p['name'] = p['name'] + ' ' + opt['label']
            p['price'] = p['price'] + Decimal(opt['price'])
            p['identifier'] = p['identifier'] + ':' + opt['id']
            yield p
