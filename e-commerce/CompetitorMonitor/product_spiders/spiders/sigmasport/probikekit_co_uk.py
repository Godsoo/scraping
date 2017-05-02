# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import json
import copy

from product_spiders.base_spiders.primary_spider import PrimarySpider

from sigmasportitems import SigmaSportMeta, extract_exc_vat_price

class ProbikekitSpider(PrimarySpider):
    name = u'sigmasport-probikekit.co.uk'
    allowed_domains = ['www.probikekit.co.uk']
    # start_urls = [
    #     'http://www.probikekit.co.uk/elysium.search?search=&pageNumber=1&searchFilters=&switchcurrency=GBP'
    # ]
    start_urls = ['http://www.probikekit.co.uk']

    csv_file = 'probikekit.co.uk_crawl.csv'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//a[@class="js-nav-item-link"]/@href').extract()
        categories += hxs.select('//div[@class="submenu-column"]//li/a/@href').extract()
        for url in categories:
            if url.endswith('.list'):
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #categories
        for url in hxs.select('//div[@class="list-menu"]//a/@href').extract():
            if url.endswith('.list'):
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)
        # pagination
        pages = response.css('.pagination_pageNumber::attr(href)').extract()
        for url in pages:
            yield Request(response.urljoin(url), callback=self.parse_products_list)
        # if not pages:
        #     self.log('Error! No next page found! {}'.format(response.url))
        #     retry = response.meta.get('retry', 0)
        #     if retry < 10:
        #         meta = response.meta.copy()
        #         meta['retry'] = retry + 1
        #         yield Request(response.url,
        #                       meta=meta,
        #                       callback=self.parse_products_list,
        #                       dont_filter=True)
        # products
        products = hxs.select('//div[@class="row line productlist"]//p[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url + '?switchcurrency=GBP'),
                          callback=self.parse_product,
                          meta={'dont_merge_cookies': True})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//div[@class="product-image main-product-image"]//img[@class="product-img"]/@src').extract()
        try:
            product_identifier = hxs.select('//*[@id="productId"]/@value').extract()[0].strip()
        except:
            self.log('Error! No product ID on the page! {}'.format(response.url))
            retry = response.meta.get('retry', 0)
            if retry < 10:
                meta = response.meta.copy()
                meta['retry'] = retry + 1
                meta['dont_merge_cookies'] = True
                yield Request(response.url,
                              meta=meta,
                              callback=self.parse_product,
                              dont_filter=True)
            return
        product_name = hxs.select('//div[@class="product-title-wrap"]/h1/text()').extract()[0].strip()
        category = response.url.split('/')[3].replace('-', ' ').title()
        brand = response.xpath('//th[contains(text(),"Brand:")]/../td//text()[normalize-space(.)!=""]').extract()
        brand = brand[0].strip() if brand else ''
        product_price = response.css('span.price::text').extract_first()
        product_price = extract_price(product_price)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('sku', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        product_loader.add_value('price', product_price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('brand', brand)
        product_loader.add_value('category', category)
        if product_price < 10:
            product_loader.add_value('shipping_cost', 1.99)
        else:
            product_loader.add_value('shipping_cost', 0)
        product = product_loader.load_item()

        variations = hxs.select('//div[@class="variation-dropdowns fl"]/form//input[@name="variation"]/@value').extract()

        product_options = hxs.select('//div[@class="variation-dropdowns fl"]/form[1]//select/option/@value').extract()
        if product_options:
            for option_id in product_options:
                if option_id:
                    yield Request('http://www.probikekit.co.uk/variations.json?productId=' + product_identifier + '&selected=1&variation1=' + variations[0] + '&option1=' + option_id + '&switchcurrency=GBP',
                                  meta={'product': product, 'cur_variation': 1},
                                  callback=self.parse_product_option)
        else:
            metadata = SigmaSportMeta()
            metadata['price_exc_vat'] = extract_exc_vat_price(product)
            product['metadata'] = metadata
            yield product

    def parse_product_option(self, response):
        base_url = get_base_url(response)
        product_data = json.loads(response.body)

        if 'variations' not in product_data or not product_data['variations']:
            self.log('Error! No options on the page! {}'.format(response.url))
            retry = response.meta.get('retry', 0)
            if retry < 10:
                meta = response.meta.copy()
                meta['retry'] = retry + 1
                yield Request(response.url,
                              meta=meta,
                              callback=self.parse_product_option,
                              dont_filter=True)

        product = response.meta['product']
        cur_variation = response.meta['cur_variation']

        if cur_variation == len(product_data['variations']):
            name = ''
            for variation in product_data['variations']:
                name += ' ' + variation['options'][0]['name']
            name = name.replace('One Colour', '').replace('One Option', '').replace('One Option', '')
            name = ' '.join(name.split())
            new_item = copy.deepcopy(product)
            new_item['name'] += ' ' + name
            new_item['identifier'] = str(product_data['selected-product-id'])
            new_item['price'] = extract_price(product_data['price'].split(';')[1])
            if new_item['price'] < 10:
                new_item['shipping_cost'] = 1.99
            else:
                new_item['shipping_cost'] = 0
            if product_data['images']:
                new_item['image_url'] = urljoin_rfc('http://s1.thcdn.com/', product_data['images'][2]['name'])

            metadata = SigmaSportMeta()
            metadata['price_exc_vat'] = extract_exc_vat_price(new_item)
            new_item['metadata'] = metadata
            yield new_item
        else:
            base_url = 'http://www.probikekit.co.uk/variations.json?productId='
            base_url += str(product['identifier']) + '&selected=' + str(cur_variation + 1) + '&switchcurrency=GBP'
            i = 0
            for variation in product_data['variations'][0:cur_variation]:
                i += 1
                base_url += '&variation' + str(i) + '=' + str(variation['id'])
                base_url += '&option' + str(i) + '=' + str(variation['options'][0]['id'])
            i += 1
            for option in product_data['variations'][cur_variation]['options']:
                url = base_url + '&variation' + str(i) + '=' + str(product_data['variations'][cur_variation]['id'])
                url += '&option' + str(i) + '=' + str(option['id'])
                yield Request(url,
                              meta={'product': product, 'cur_variation': cur_variation + 1},
                              callback=self.parse_product_option)
