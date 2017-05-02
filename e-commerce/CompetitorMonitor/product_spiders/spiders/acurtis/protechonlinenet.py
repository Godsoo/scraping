from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from w3lib.url import urljoin_rfc

from product_spiders.utils import extract_price

import json
from itertools import product


class ProtechOnlineSpider(BaseSpider):
    name = u'protechonline.net'
    allowed_domains = ['www.protechonline.net']
    start_urls = [u'http://www.protechonline.net']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # Categories
        for url in hxs.select('//a[@class="category-link"]/@href').extract():
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        for url in hxs.select('//*[@class="CategoryChildCategories"]//a/@href').extract():
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        # Pages
        for url in hxs.select('//ul[@class="pagination"]//a[not(contains(@href, "#"))]/@href').extract():
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        # Products
        for url in hxs.select('//a[@class="category-item-name"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_xpath('name', '//*[@itemprop="name"]/text()')
        product_loader.add_xpath('brand', '//*[@itemprop="manufacturer"]/@content')
        img_src = hxs.select('//a[@itemprop="image"]/img/@src').extract()
        if img_src:
            product_loader.add_value('image_url', urljoin_rfc(base_url, img_src[0]))
        price = hxs.select('//*[@itemprop="price"]//*[@id="lblPrice"]').re(r'([\d,.]+)')
        if not price:
            price = hxs.select('//*[@itemprop="price"]//*[@id="lblSalePrice"]').re(r'([\d,.]+)')
            if not price:
                price = 0
        product_loader.add_value('price', price)
        product_loader.add_value('category', hxs.select('//*[@id="lblCategoryTrail"]//a/text()')[-1].extract())
        product_loader.add_xpath('identifier', '//input[@id="hfItemID"]/@value')
        product_loader.add_xpath('sku', '//input[@id="hfItemID"]/@value')
        product_loader.add_value('url', response.url)

        product_item = product_loader.load_item()

        ajax_url = 'http://www.protechonline.net/Store/Controls/ScriptService.asmx/GetPrice'

        params = {
            'itemID': int(product_item['identifier']),
            'personalizationIds': [],
            'personalizationStrings': [],
            'quantity': 1,
            'variantIDs': [],
        }

        options_select = hxs.select('//div[@id="dvProductVariations"]//select')
        if options_select:
            options_variants = product(*[opt.select('option') for opt in options_select])
            for variant in options_variants:
                variant_name = ' '.join([opt.select('text()').extract()[0].split('/')[0] for opt in variant])
                variant_ids_list = [int(opt.select('@value').extract()[0]) for opt in variant]
                variant_id = '_'.join([str(ident) for ident in variant_ids_list])

                option_item = Product(product_item)
                option_item['name'] = product_item['name'] + ' ' + variant_name
                option_item['identifier'] = product_item['identifier'] + '_' + variant_id

                params['variantIDs'] = variant_ids_list

                yield Request(ajax_url, method='POST', body=json.dumps(params),
                              headers={'Content-Type': 'application/json; charset=utf-8'},
                              dont_filter=True,
                              callback=self.parse_ajax_price,
                              meta={'product_item': option_item})
        else:
            yield product_item

    def parse_ajax_price(self, response):
        result = json.loads(response.body)

        product_loader = ProductLoader(item=Product(response.meta['product_item']), response=response)
        price = extract_price(result['d']['price'])

        product_loader.add_value('price', price)

        yield product_loader.load_item()
