import re
import csv
import json
import itertools
from StringIO import StringIO


from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.exceptions import DontCloseSpider

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url

from decimal import Decimal

from scrapy import log

from utils import extract_price_eu as extract_price


class MeublesconceptSpider(BaseSpider):
    name = 'voga_fr-meublesconcept.fr'
    allowed_domains = ['meublesconcept.fr']
    start_urls = ('http://www.meublesconcept.fr',)

    def __init__(self, *args, **kwargs):
        super(MeublesconceptSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_products, signals.spider_idle)

        self.collect_products = []
        self.sync_calls = False

    def process_products(self, spider):
        if spider.name == self.name:
            if self.collect_products and not self.sync_calls:
                self.sync_calls = True
                product = self.collect_products[0]

                meta = product
                meta['collect_products'] = self.collect_products[1:]
                req = FormRequest('http://www.meublesconcept.fr/ajax_add_cart.php',
                                  formdata=product['formdata'],
                                  dont_filter=True,
                                  callback=self.parse_add_product,
                                  meta=meta)

                log.msg('SEND REQ')
                self._crawler.engine.crawl(req, self)
                raise DontCloseSpider

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories= hxs.select('//table[tr/td/span/text()="Produits"]//a/@href').extract()
        for category in categories:
            yield Request(category)

        products = hxs.select('//a[@class="pdte"]/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product)

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brand = hxs.select("//*[contains(text(),'Designer:')]/text()").extract()
        brand = brand[0].split(':')[1].strip() if brand else ''

        name = hxs.select('//td[@class="cont_heading_td"]//h1/text()').extract()[0]
        identifier = hxs.select('//input[@name="products_id"]/@value').extract()
        if identifier:
            identifier = identifier[0]
        else:
            identifier = re.search('p-(\d+).html', response.url)
            if identifier:
                identifier = identifier.group(1)
            else:
                log.msg('PRODUCT WIHTOUT IDENTIFIER: ' + response.url)
                return

        image_url = hxs.select('//a[@rel="fotografias"]/img/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        category = hxs.select('//td[@class="cont_heading_td"]/span/text()').extract()
        sku = hxs.select('//tr/td[contains(text(), "Ref: ")]/text()').re('Ref: (.*)')

        price = hxs.select('//td[@class="preu"]/text()').extract()
        price = price[0] if price else '0'
        price = extract_price(price)

        options = self.get_options(response, price)
        if options:
            for option in options:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('url', response.url.split('?osCsid=')[0])
                loader.add_value('name', name+option[1])
                loader.add_value('image_url', image_url)
                loader.add_value('brand', brand)
                loader.add_value('identifier', identifier+'-'.join(option[0]))
                loader.add_value('category', category)
                loader.add_value('sku', sku)
                loader.add_value('price', option[2])
                out_of_stock = hxs.select('//form[contains(@id, "cart_quantity_")]/img[contains(@alt, "OUT_STOCK")]')
                if out_of_stock:
                    loader.add_value('stock', 0)

                formdata = {'products_id':identifier}
                for option_id in option[0]:
                    attr_id = hxs.select('//select[option[@value="'+option_id+'"]]/@id').re('(\d+)')[0]
                    formdata['attribute_'+attr_id] = option_id

                product = {'product': loader.load_item(),
                           'formdata': formdata}
                self.collect_products.append(product)
        else:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            loader.add_value('image_url', image_url)
            loader.add_value('brand', brand)
            loader.add_value('identifier', identifier)
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('price', price)
            out_of_stock = hxs.select('//form[contains(@id, "cart_quantity_")]/img[contains(@alt, "OUT_STOCK")]')
            if out_of_stock:
                loader.add_value('stock', 0)
            formdata = {'products_id':identifier}
            product = {'product': loader.load_item(),
                       'formdata': formdata}
            self.collect_products.append(product)

    def parse_add_product(self, response):
        url = "http://www.meublesconcept.fr/shopping_cart.php"
        yield Request(url, dont_filter=True, callback=self.parse_basket_product, meta=response.meta)

    def parse_basket_product(self, response):
        hxs = HtmlXPathSelector(response)
        shipping_url = "http://www.meublesconcept.fr/ship_estimator.php?action=process"
        formdata = {'shipcountry':'73',
                    'state': 'Ile-de-france'}

        clean = hxs.select('//a[contains(@href, "remove")]/@href').extract()[0]

        meta = response.meta
        meta['clean'] = clean

        req = FormRequest(shipping_url,
                          formdata=formdata,
                          dont_filter=True,
                          callback=self.parse_shipping,
                          meta=meta)
        yield req

    def parse_shipping(self, response):
        hxs = HtmlXPathSelector(response)
        shipping_cost = ''.join(hxs.select('//tr[td[contains(text(), "Envoyer")]]/td/text()').re('(\d+,\d+)'))
        shipping_cost = extract_price(shipping_cost)

        product = response.meta['product']
        product['shipping_cost'] = shipping_cost
        yield product

        yield Request(response.meta['clean'],
                      callback=self.parse_sync_basket,
                      dont_filter=True,
                      meta={'collect_products': response.meta['collect_products']})

    def parse_sync_basket(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta
        collect_products = meta['collect_products']
        if collect_products:
            product = collect_products[0]
            meta = product
            meta['collect_products'] = collect_products[1:]

            req = FormRequest('http://www.meublesconcept.fr/ajax_add_cart.php',
                              formdata=product['formdata'],
                              dont_filter=True,
                              callback=self.parse_add_product,
                              meta=meta)
            yield req


    def get_options(self, response, base_price):
        hxs = HtmlXPathSelector(response)
        options = []
        options_containers = hxs.select('//select[contains(@id, "id[")]')

        combined_options = []
        for options_container in options_containers:
            element_options = []
            for option in options_container.select('option'):
                option_id = option.select('@value').extract()[0]
                option_split = option.select('text()').extract()[0].split(' (+')
                option_desc = option_split[0]
                option_add_price = ''.join(option.select('text()').re('(\d+,\d+)'))
                option_add_price = extract_price(option_add_price) if option_add_price else extract_price('0')
                element_options.append((option_id, option_desc, option_add_price))
            combined_options.append(element_options)

        combined_options = list(itertools.product(*combined_options))
        for combined_option in combined_options:
            name, option_ids, price = '', [], 0
            for option in combined_option:
                option_ids.append(option[0])
                name = name + ' - ' + option[1]
                price = Decimal(price) + option[2]
            options.append((option_ids, name, price+base_price))
        return options
