# -*- coding: utf-8 -*-
import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class SimplyGardenFurnitureSpider(BaseSpider):
    name = 'simplygardenfurniture.co.uk'
    allowed_domains = ['simplygardenfurniture.co.uk']
    start_urls = ('http://simplygardenfurniture.co.uk',)

    def start_requests(self):
        brands = ({'url': u'http://www.simplygardenfurniture.co.uk/Keter-UK', 'name': u'Keter'},
                  {'url': u'http://www.simplygardenfurniture.co.uk/Suncast', 'name': u'Suncast'})
        for brand in brands:
            yield Request(brand['url'], meta={'brand': brand['name']}, callback=self.parse_brand)

    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response)

#         categories = hxs.select(u'//a[child::span]/@href').extract()
#         for url in categories:
#             url = urljoin_rfc(get_base_url(response), url)
#             yield Request(url, meta=response.meta, callback=self.parse_brand)

        pages = hxs.select(u'//ul[@class="pagination"]//a/@href').extract()
        for page_url in pages:
            next_page = urljoin_rfc(get_base_url(response), page_url)
            yield Request(next_page, meta=response.meta, callback=self.parse_brand)

        products = hxs.select(u'//div[contains(@class,"product-box")]//h4/a/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

    def parse(self, response):
        pass

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        category = hxs.select('//div[@id="top-breadcrumb"]/ol[@class="breadcrumb"]//a/text()').extract()[-1]
        identifier = hxs.select('//ul[@id="select-product-option"]/@data-product-id').extract()[0]
        image_url = hxs.select('//meta[@itemprop="image"]/@content').extract()[0]

        name = hxs.select('//meta[@itemprop="name"]/@content').extract()[0].strip()
        for option in hxs.select('//ul[@id="select-product-option"]/li[contains(@class, "product-options-list")]'):
            option_name = option.select('.//span[@class="product-option-name"]/text()').extract()[0].strip()

            option_identifier = option.select('@data-option-id').extract()
            if option_identifier:
                option_identifier = identifier + '-' + option_identifier[0]
            else:
                option_identifier = identifier

            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('url', response.url)
            loader.add_value('name', u'%s %s' % (name, option_name))
            loader.add_value('identifier', option_identifier)
            loader.add_value('category', category)
            loader.add_value('image_url', image_url)

            price = option.select('.//span[@class="price"]/strong/text()').extract()
            if not price:
                price = option.select('.//div/div[@class="now-price"]/strong/text()').extract()

            loader.add_value('price', price[0] if price else u'0.00')
            loader.add_value('brand', response.meta['brand'].strip().lower())

            # reviews_url = hxs.select(u'//div[@id="reviews-container"]//a[@class="view-al-test"]/@href').extract()

            product = loader.load_item()

            metadata = KeterMeta()
            metadata['brand'] = response.meta['brand'].strip().lower()
            metadata['reviews'] = []
            product['metadata'] = metadata

            yield product

    def parse_review(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        reviews = hxs.select(u'//div[@class="boxproductinfo"]/table/tr')
        product = response.meta['product']

        if not reviews:
            yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%d/%m/%Y')
            loader.add_value('date', review.select(u'./td/div/p/span/text()').re(u'(\d{2}/\d{2}/\d{4})')[0])
            loader.add_xpath('full_text', u'./td/div[2]/text()')
            loader.add_value('url', response.url)

            product['metadata']['reviews'].append(loader.load_item())

        next_page = hxs.select(u'//h4/a[contains(text(),"Next")]/@href').extract()

        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, meta={'product': product}, callback=self.parse_review)
        else:
            yield product
