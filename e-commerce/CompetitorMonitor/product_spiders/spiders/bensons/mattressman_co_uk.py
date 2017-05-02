import re
import json
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.item import Item, Field

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class Meta(Item):
    net_price = Field()

class MattressManSpider(BaseSpider):
    name = 'bensons_mattressman.co.uk'
    allowed_domains = ['mattressman.co.uk']
    start_urls = ['http://www.mattressman.co.uk/']

    def _start_requests(self):
        yield Request('http://www.mattressman.co.uk/handlers/JSON.ashx?req=Product&ProductID=46437', callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//div[@id="slidemenu"]/ul/li/a'):
            for url in cat.select('..//a/@href').extract():
                yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list, meta={'category': ''.join(cat.select('./text()').extract())})

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//div[@id="ctl00_ctl00_body_stdBody_landingPageTypes"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list, meta=response.meta)
        for url in hxs.select('//div[@id="ctl00_ctl00_body_stdBody_productTypes"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list, meta=response.meta)
        for url in hxs.select('//div[@id="ctl00_ctl00_body_stdBody_landingPageSubMenu"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list, meta=response.meta)
        found = False
        for id in hxs.select('//div[contains(@class,"product-list-item")]//div[@id]/@id').extract():
            try:
                _ = int(id)
                found = True
                yield Request('http://www.mattressman.co.uk/handlers/JSON.ashx?req=Product&ProductID=' + id, callback=self.parse_product, meta=response.meta)
            except:
                pass
        if not found:
            self.log('No products on %s' % response.url)


    def parse_product(self, response):
        data = json.loads(response.body)

        product = Product()
        product['sku'] = data['id']
        product['identifier'] = data['id']
        product['name'] = self.html_expand(data['name'])
        product['brand'] = data['manufacturer']['name']
        product['category'] = response.meta['category']
        found = False
        options = data['variations']
        try:
            sizes = data['bedsizes']
            for size in sizes:
                found = True
                for opt in options:
                    if opt['bedSize']['id'] == size['id']:
                        url = opt['url']
                yield FormRequest(url='https://www.mattressman.co.uk/handlers/JSON.ashx?req=changeVariation', formdata={'prodid':str(product['identifier']), 'sizeid':str(size['id'])}, dont_filter=True, meta={'product':product, 'url':url}, callback=self.parse_options)
                
        except KeyError:
            for opt in options:
                prod = Product(product)
                prod['identifier'] = opt['id']
                prod['name'] = self.html_expand(opt['name'])
                prod['url'] = urljoin_rfc(get_base_url(response), opt['url'])
                prod['price'] = extract_price(opt['price'])
                prod['stock'] = opt['stock']
                try:
                    # All products with a price are to be set as 'In Stock'
                    if int(prod['stock']) == 0 and prod['price']:
                        prod['stock'] = '1'
                except:
                    pass
                prod['image_url'] = urljoin_rfc(get_base_url(response), opt.get('images800', opt.get('images500'))[0].get('src'))
                found = True
                price = Decimal(prod['price'])
                net_price = price / Decimal('1.2')

                meta_ = Meta()
                meta_['net_price'] = str(net_price)
                prod['metadata'] = meta_

                yield prod
            
         
        if not found:
            self.log('Options not found on %s' % (response.url))
            if product.get('price'):
                price = Decimal(product['price'])
                net_price = price / Decimal('1.2')

                meta_ = Meta()
                meta_['net_price'] = str(net_price)
                product['metadata'] = meta_

            yield product

    def parse_options(self, response):
        data = json.loads(response.body)
        divans = data['divans']
        variations = data['variations']
        product = response.meta['product']
        url = response.meta['url']
        found = False
        for divan in divans.itervalues():
            for opt in divan:
                prod = Product(product)
                prod['identifier'] = product['identifier'] + '-' + opt['id']
                prod['name'] = product['name'] + ' ' + self.html_expand(opt['name'])
                prod['url'] = urljoin_rfc(get_base_url(response), url.split('.')[0] + opt['divanPartURL'] + '.' + url.split('.')[1])
                prod['price'] = extract_price(opt['price']) + extract_price(variations[0]['price'])
                prod['stock'] = opt['stock']
                try:
                    # All products with a price are to be set as 'In Stock'
                    if int(prod['stock']) == 0 and prod['price']:
                        prod['stock'] = '1'
                except:
                    pass
                if 'PID' in opt['image']:
                    prod['image_url'] = urljoin_rfc(get_base_url(response), variations[0].get('images800', variations[0].get('images500'))[0].get('src'))
                else:
                    prod['image_url'] = urljoin_rfc(get_base_url(response), opt['image'])
                found = True
                price = Decimal(prod['price'])
                net_price = price / Decimal('1.2')

                meta_ = Meta()
                meta_['net_price'] = str(net_price)
                prod['metadata'] = meta_

                yield prod

        if not found:
            for opt in variations:
                prod = Product(product)
                prod['identifier'] = opt['id']
                prod['name'] = self.html_expand(opt['name'])
                prod['url'] = urljoin_rfc(get_base_url(response), opt['url'])
                prod['price'] = extract_price(opt['price'])
                prod['stock'] = opt['stock']
                try:
                    # All products with a price are to be set as 'In Stock'
                    if int(prod['stock']) == 0 and prod['price']:
                        prod['stock'] = '1'
                except:
                    pass
                prod['image_url'] = urljoin_rfc(get_base_url(response), opt.get('images800', opt.get('images500'))[0].get('src'))
                found = True
                price = Decimal(prod['price'])
                net_price = price / Decimal('1.2')

                meta_ = Meta()
                meta_['net_price'] = str(net_price)
                prod['metadata'] = meta_

                yield prod
            

    def html_expand(self, s):
        return s.replace('&#34;', '"')
        