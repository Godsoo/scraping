# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import os
import re

from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader.processor import MapCompose, TakeFirst

from base_spiders.target.targetspider import BaseTargetSpider, TargetReviewLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class LegoUSATargetReviewLoader(TargetReviewLoader):
    product_url_in = MapCompose(unicode, unicode.strip)
    product_url_out = TakeFirst()


class TargetSpider(BaseTargetSpider):
    name = 'legousa-target.com'
    start_urls = ['http://tws.target.com/searchservice/item/search_results/v2/by_keyword?search_term=lego&alt=json&pageCount=900000&response_group=Items&zone=mobile&offset=0']

    ReviewLoaderCls = LegoUSATargetReviewLoader

    _re_sku = re.compile('(\d\d\d\d\d?)')

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'target_map_deviation.csv')

    def _load_product_json_data_to_loader(self, response):
        loader = super(TargetSpider, self)._load_product_json_data_to_loader(response)
        name = loader.get_output_value('name')
        sku = self._re_sku.findall(name)
        sku = max(sku, key=len) if sku else ''
        loader.replace_value('sku', sku)
        return loader

    # def parse_product(self, response):
    #     try:
    #         request = super(TargetSpider, self).parse_product(response).next()
    #     except StopIteration:
    #         return
    #     product = request.meta.get('product')
    #     if product:
    #
    #
    #         request.meta['product'] = product
    #     yield request

    def get_review_full_text(self, review):
        title = review['Title']
        text = review['ReviewText']
        if title:
            full_text = title + ' #&#&#&# ' + text
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
