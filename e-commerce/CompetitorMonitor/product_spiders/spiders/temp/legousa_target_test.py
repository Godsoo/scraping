# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import os
import json
import re
from urlparse import urljoin as urljoin_rfc

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader.processor import MapCompose, TakeFirst

from base_spiders.target.targetspider import BaseTargetSpider, TargetReviewLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class LegoUSATargetReviewLoader(TargetReviewLoader):
    product_url_in = MapCompose(unicode, unicode.strip)
    product_url_out = TakeFirst()


class TargetTestSpider(BaseTargetSpider):
    name = 'legousa-target.com-test'
    start_urls = ['http://www.target.com/s?searchTerm=lego&category=0%7CAll%7Cmatchallpartial%7Call+categories&kwr=y#?lnk=snav_rd_lego_sale']

    ReviewLoaderCls = LegoUSATargetReviewLoader

    _re_sku = re.compile('(\d\d\d\d\d?)')

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'target_map_deviation.csv')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        # Crawl product listing
        for url in hxs.select('//ul[@class="productsListView"]//div[@class="tileImage "]/a/@href').extract(): ###
            yield Request(url, callback=self.parse_product)

        # Crawl next page
        tmp = hxs.select('//div[@class="pagination-item next"]/a/@href').extract()
        if tmp:
            url = urljoin_rfc(response.url, tmp[0])
            url = 'http://www.target.com/sr?searchTerm=lego&category=0&view=medium&sort=relevance&resultsPerPage=60&page=2'
            yield Request(url, headers={'Accept':'application/json, text/javascript, */*', 'Content-Type':'application/x-www-form-urlencoded', 'X-Requested-With':'XMLHttpRequest'}, meta={'page':2}, callback=self.parse_more)

    def parse_more(self, response):
        jdata = json.loads(response.body)
        hxs = HtmlXPathSelector(text=jdata['productListArea']['productListForm'])
        # Crawl product listing
        urls = hxs.select('//ul[@class="productsListView"]//div[@class="tileImage "]/a/@href').extract()
        for url in urls: ###
            yield Request(url, callback=self.parse_product)

        # Crawl next page
        hxs = HtmlXPathSelector(text=jdata['productListArea']['pagination1'])
        tmp = hxs.select('//a[span="Next page"]/@href').extract()
        if tmp:
            page = response.meta['page'] + 1
            url = 'http://www.target.com/sr?searchTerm=lego&category=0&view=medium&sort=relevance&resultsPerPage=60&page=%s' % str(page)
            yield Request(url, headers={'Accept':'application/json, text/javascript, */*', 'Content-Type':'application/x-www-form-urlencoded', 'X-Requested-With':'XMLHttpRequest'}, meta={'page':page}, callback=self.parse_more)

    def parse_product(self, response):
        try:
            request = super(TargetTestSpider, self).parse_product(response).next()
        except StopIteration:
            return
        product = request.meta.get('product')
        if product:
            sku = self._re_sku.findall(product['name'])
            product['sku'] = sku[0] if sku else ''
            product['brand'] = 'LEGO'

            price = product['price']

            if price:
                stock = 1
            else:
                price = 0
                stock = 0

            hxs = HtmlXPathSelector(response)
            tmp = hxs.select('//div[@class="oneButtonSystem"]').extract()
            if tmp and 'out of stock' in tmp[0].lower():
                stock = 0

            product['price'] = price
            product['stock'] = stock

            request.meta['product'] = product
        yield request

    def get_review_full_text(self, review):
        title = review['Title']
        text = review['ReviewText']
        if title:
            full_text = title + '\n' + text
        else:
            full_text = text
        extra_text = ''
        pros = review['Pros']
        cons = review['Cons']
        if pros:
            extra_text += '\nPros: ' + ', '.join(pros)
        if cons:
            extra_text += '\nCons: ' + ', '.join(cons)
        if 'Entertaining' in review['SecondaryRatings']:
            extra_text += '\nEntertaining: %s' % review['SecondaryRatings']['Entertaining']['Value']
        if 'Quality' in review['SecondaryRatings']:
            extra_text += '\nQuality: %s' % review['SecondaryRatings']['Quality']['Value']
        if 'Value' in review['SecondaryRatings']:
            extra_text += '\nValue: %s' % review['SecondaryRatings']['Value']['Value']
        if review['IsRecommended']:
            extra_text += '\nYes, I recommend this product.'
        if extra_text:
            full_text += ' #&#&#&# ' + extra_text
        return full_text
