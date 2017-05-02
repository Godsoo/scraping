# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import json
import re


class MusclefoodSpider(BaseSpider):
    name = u'usn-musclefood.com'
    allowed_domains = ['musclefood.com']
    start_urls = []

    def start_requests(self):
        brands = {'Sci-MX': ['http://www.musclefood.com/supplements/sci-mx.html'],
        'Optimum Nutrition': ['http://www.musclefood.com/supplements/optimum-nutrition.html'],
        'BSN': ['http://www.musclefood.com/supplements/bsn-supplements.html'],
        'PhD': ['http://www.musclefood.com/supplements/phd-supplements.html'],
        'Maxi Nutrition': ['http://www.musclefood.com/catalogsearch/result/?order=relevance&dir=desc&a=all&q=Maxi+Nutrition'],
        'Reflex': ['http://www.musclefood.com/supplements/reflex-nutrition.html'],
        'Cellucor': ['http://www.musclefood.com/catalogsearch/result/?order=relevance&dir=desc&a=all&q=cellucor'],
        'USN': ['http://www.musclefood.com/supplements/usn-supplements.html']}

        for brand, brand_urls in brands.items():
            for brand_url in brand_urls:
                yield Request(brand_url, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), meta=response.meta)

        # products
        for url in hxs.select('//div[@class="category-products"]//div[@class="product-panel"]/div[@class="product-panel-image"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//*[@id="image"]/@src').extract()
        try:
            product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0].strip()
        except:
            product_identifier = hxs.select('//form[@id="product_addtocart_form"]/@action').re(r'/product/(\d+)')[0]
        product_name = hxs.select('//*[@id="productname"]/text()').extract()[0]
        category = hxs.select('//div[@class="breadcrumbs"]//a/text()').extract()[1:]
        sku = product_identifier

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            attributes = {}
            for attr_id, attr in product_data['attributes'].iteritems():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' '.join((products.get(product, ''), option['label']))
                        attributes.setdefault(product, []).append({'attr_id': attr_id, 'val': option['id']})

            for identifier, option_name in products.iteritems():
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', product_identifier + '_' + identifier)
                product_loader.add_value('name', product_name + option_name)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', category)
                product_loader.add_value('sku', sku)
                product_loader.add_value('brand', response.meta.get('brand'))

                product = product_loader.load_item()
                form_data = {'product': product_identifier,
                             'billing_qty': '1'}
                for attr in attributes[identifier]:
                    form_data['super_attribute[{}]'.format(attr['attr_id'])] = str(attr['val'])
                yield FormRequest(url='http://www.musclefood.com/billing/ajax/servingsinfo/',
                                  formdata=form_data,
                                  meta={'product': product},
                                  callback=self.parse_price,
                                  dont_filter=True)

        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = ''.join(hxs.select('//span[@class="price"]/text()').extract()).strip()
            price = extract_price(price)
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('category', category)
            product_loader.add_value('sku', sku)
            product_loader.add_value('brand', response.meta.get('brand'))
            if price < 75:
                product_loader.add_value('shipping_cost', 3.95)
            product = product_loader.load_item()
            yield product

    @staticmethod
    def parse_price(response):
        data = json.loads(response.body)
        product = response.meta['product']
        price = extract_price(data['final_price'])
        product['price'] = price
        if price < 75:
            product['shipping_cost'] = 3.95
        if data['stock'] == '1':
            product['stock'] = 0
        yield product
