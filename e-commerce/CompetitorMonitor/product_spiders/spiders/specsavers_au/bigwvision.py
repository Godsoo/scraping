# -*- coding: utf-8 -*-
"""
Extract all products without options

Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4566-specsavers-au---new-site---big-w-vision/details
"""
import os
import time
import json

from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest
try:
    from scrapy.selector import Selector
except ImportError:
    from scrapy.selector import HtmlXPathSelector as Selector

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from specsaversitems import SpecSaversMeta

HERE = os.path.abspath(os.path.dirname(__file__))

get_epoch = lambda: int(time.time())

class BigWVision(BaseSpider):
    name = 'specsavers_au-bigwvision.com.au'
    allowed_domains = ('bigwvision.com.au',)
    start_urls = ('https://www.bigwvision.com.au/',)

    product_list_url = 'https://www.bigwvision.com.au/WebServicesAjax.asmx/ProductSearchWithListTemplate?rand={rand}'
    req_headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Accept-Encoding': 'gzip, deflate',
                   'Accept-Language': 'es-419,es;q=0.8,en;q=0.6',
                   'Cache-Control': 'max-age=0',
                   'Connection': 'keep-alive',
                   'Content-Type': 'application/json',
                   'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) '
                                 'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36',
                   'X-Requested-With': 'XMLHttpRequest'}
    req_body = '{{"searchString":"{categ}","filter":"","skip":{skip},"listTemplateName":"ProductCategorySearchItem",' \
               '"take":{per_page},"orderBy":"ProductPrice","requestedDeliveryDate":null}}'
    per_page = 24

    def parse(self, response):
        categories = response.xpath('//li[@class="MenuDropdownArea"]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url), callback=self.parse_category)

    def parse_category(self, response):
        category_code = response.xpath('//input[@id="currentCategoryCode"]/@value').extract()
        categories = response.xpath('//div[@id="Breadcrumbs"]/span/a/text()')[1:].extract()

        meta = {'skip': 0, 'category_code': category_code[0], 'categories': categories}

        req = FormRequest(self.product_list_url.format(rand=get_epoch()),
                          headers=self.req_headers,
                          method='POST',
                          body=self.req_body.format(categ=category_code[0], skip=0, per_page=self.per_page),
                          meta=meta,
                          callback=self.parse_product_list)
        yield req

    def parse_product_list(self, response):
        data = json.loads(response.body)
        meta = response.meta
        product_list = json.loads(data['d'])
        record_count = int(product_list['recordCount'])
        skip = meta.get('skip', 0)
        if skip < record_count:
            meta['skip'] += self.per_page
            req = FormRequest(self.product_list_url.format(rand=get_epoch()),
                              headers=self.req_headers,
                              method='POST',
                              body=self.req_body.format(categ=meta['category_code'], skip=meta['skip'],
                                                        per_page=self.per_page),
                              meta=meta,
                              callback=self.parse_product_list)
            yield req
        for product in product_list['products']:
            loader = ProductLoader(item=Product(), response=response)
            sel = Selector(text=product['listContent'])
            loader.add_value('name', product['description'])
            loader.add_value('sku', product['productCode'])
            loader.add_value('identifier', product['productCode'])
            # the price returned in the HTML for contact lenses is a discount price
            # so for those the 'price' field is used, the field can't be used for all
            # products because it's incorrect for most items.
            if 'contact lenses' in ' '.join(meta['categories']).lower():
                loader.add_value('price', product['price'])
            else:
                price = sel.select('.//span[@class="ProductPriceLabel"]/text()').extract()
                loader.add_value('price', price)
            url = sel.select('.//a/@href').extract()
            loader.add_value('url', response.urljoin(url[0]))
            image_url = sel.select('.//img/@src').extract()
            loader.add_value('image_url', response.urljoin(image_url[0]))
            loader.add_value('shipping_cost', '7.95')
            for category in meta['categories']:
                loader.add_value('category', category)
            item = loader.load_item()

            metadata = SpecSaversMeta()
            promotion = map(lambda x: x.strip(), sel.select('.//h4[@class="ContactLens"]//text()').extract())
            promotion = ' '.join(promotion).strip()
            metadata['promotion'] = promotion if promotion else ''
            item['metadata'] = metadata
            yield item

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1[@itemprop="name"]/text()').extract()
        if not name:
            name = response.xpath('//script[contains(text(), "ec:addProduct")]').re('name\': \'(.*)\',')
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))
        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        if not price:
            price = response.xpath('//script[contains(text(), "ec:addProduct")]').re('price\': (.*)')
        loader.add_value('price', price)
        categories = response.xpath('//div[@class="breadcrumbs"]/a/text()')[1:].extract()
        for category in categories:
            loader.add_value('category', category)
        brand = response.xpath('//a[@itemprop="brand"]/text()').extract()
        if not brand:
            brand = response.xpath('//script[contains(text(), "ec:addProduct")]').re('brand\': \'(.*)\',')
        loader.add_value('brand', brand[0])
        sku = response.xpath('//h2[@class="blueH2" and contains(text(),"SKU")]/text()').re('SKU (.*)')
        loader.add_value('sku', sku)
        identifier = response.xpath('//script[contains(text(), "ec:addProduct")]').re('id\': \'(.*)\',')
        loader.add_value('identifier', identifier)
        yield loader.load_item()
