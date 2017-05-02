import re
import json
from decimal import Decimal

# from scrapy.spider import BaseSpider
from scrapy.contrib.spiders import SitemapSpider
try:
    from scrapy.selector import Selector
except:
    from scrapy.selector import HtmlXPathSelector as Selector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.utils.response import get_base_url

from itertools import product as iter_product

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class BeautytimetherapiesSpider(SitemapSpider):
    name = 'facethefuture-beautytimetherapies.co.uk'
    allowed_domains = ['beautytimetherapies.co.uk']
    # start_urls = ['https://www.beautytimetherapies.co.uk/']
    sitemap_urls = ['http://www.beautytimetherapies.co.uk/sitemap-index.xml']
    sitemap_follow = ['/sitemap-products']
    sitemap_rules = [('/', 'parse_product')]

    '''
    def start_requests(self):
        yield Request('http://www.beautytimetherapies.co.uk/skin-care-c1/suncare-tanning-c10/elemis-total-glow-self-tanning-cream-125ml-p263', callback=self.parse_product)
    '''

    '''
    def parse(self, response):
        yield FormRequest('https://www.beautytimetherapies.co.uk/customer/account/loginPost/', formdata={'login[username]':'m5l2764k@gmail.com', 'login[password]':'password'}, callback=self.login)
    '''

    '''
    def parse(self, response):
        for cat in response.xpath('//ul[@id="mp-accordion"]/li[position()>1]'):
            cattxt = cat.select('normalize-space(./a/span/text())').extract()[0]
            found = False
            for url in cat.select('./ul//a/@href').extract():
                found = True
                yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list, meta={'category': cattxt})
            if not found:
                yield Request(urljoin_rfc(get_base_url(response), cat.select('./a/@href').extract()[0]), callback=self.parse_list, meta={'category': cattxt})
    '''

    def parse_list(self, response):
        for url in response.xpath('//h2[@class="product-name"]/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product, meta=response.meta)

        for url in response.xpath('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list, meta=response.meta)

    def parse_product(self, response):
        brand = response.xpath('//meta[@itemprop="brand"]/@content').extract()
        brand = brand[0].strip() if brand else ''
        inputs_data = dict(zip(response.xpath('//input/@name').extract(), response.xpath('//input/@value').extract()))

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('sku', '//*[@id="js-product-reference"]/text()')
        loader.add_value('identifier', inputs_data['parent_product_id'])
        loader.add_value('url', response.url)
        name = response.xpath('//*[@id="js-product-title"]/text()')[0].extract().strip()
        loader.add_value('name', '{} {}'.format(brand, name))
        loader.add_xpath('price', '//*[@itemprop="price"]/@content')
        loader.add_value('category', brand)
        loader.add_value('brand', brand)
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))

        if response.xpath('//*[@id="js-product-in-stock-default"]').extract():
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        loader.add_value('shipping_cost', 0)

        prod = loader.load_item()

        parent_id = response.xpath('//input[@name="parent_product_id"]/@value').extract()[0]
        ajax_options_url = ('http://www.beautytimetherapies.co.uk/ajax/get_product_options/%(parent_id)s?'
            'cmd=addtobasket&parent_product_id=%(parent_id)s&product_id=0&image_product_id=0&image_id=0&image_index=0&') % {'parent_id': parent_id}

        yield Request(ajax_options_url, callback=self.parse_options, meta={'product': prod, 'options_url': ajax_options_url})

    def parse_options(self, response):
        product = response.meta['product']
        options_found = 0
        try:
            ajax_url = response.meta['options_url']
            data = json.loads(response.body)
            options = iter_product(*(map(lambda d: dict(attr_id=attr['id'], **d), attr['values']) for attr in data.get('attributes', []) if not attr['disabled']))
            for options_selected in options:
                new_product = Product(product)
                for option in options_selected:
                    options_found += 1
                    opt_id = 'attributes[%s]' % option['attr_id']
                    opt_value_id = option['value_id']
                    # new_product['identifier'] += ':' + opt_value_id
                    new_product['name'] += ' ' + option['value']
                    ajax_url = add_or_replace_parameter(ajax_url, opt_id, opt_value_id)
                meta = response.meta.copy()
                meta['product'] = new_product

                yield Request(ajax_url, callback=self.parse_options_prices, meta=meta)
        except Exception, e:
            self.log('NO OPTIONS WARNING => %r' % e)
            yield product
        else:
            if not options_found:
                if product.get('price'):
                    yield product
                else:
                    self.log('NO PRICE => %s' % response.url)


    def parse_options_prices(self, response):
        product = response.meta['product']

        data_option = json.loads(response.body)
        selection = data_option['selection']

        for ident, data in selection.iteritems():
            sel_price = Selector(text=data['price'])
            loader = ProductLoader(item=product, selector=sel_price)
            loader.add_xpath('price', '//span[@class="GBP"]/text()')
            loader.add_value('identifier', product['identifier'] + ':' + str(ident))
            loader.add_value('sku', data['reference'])
            yield loader.load_item()
