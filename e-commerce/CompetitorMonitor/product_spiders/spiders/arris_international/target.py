# -*- coding: utf-8 -*-

import os
import csv
from datetime import datetime
import json

from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product
from product_spiders.base_spiders.target.targetspider import BaseTargetSpider

from arrisitems import (ReviewLoader,
                        Review)

HERE = os.path.abspath(os.path.dirname(__file__))


class TargetSpider(BaseTargetSpider):
    name = 'arris_international-target.com'

    ReviewLoaderCls = ReviewLoader

    category_type = 'ordered'
    search_url = 'http://tws.target.com/searchservice/item/search_results/v2/by_keyword?search_term=%s' \
                 '&alt=json&pageCount=900000&response_group=Items&zone=mobile&offset=0'
    search_codes = [
        'SB6141',
        'SB6183',
        'SB6190',
        'SBR AC1900P',
        'SBG6580',
        'SBG6700',
        'SBG6900',
        'SBG7580',
        'SBG6700',
        'SBR AC1900P',
        'SBR AC3200P',
        'SBX AC1200P',
        'SBX 1000P'
    ]

    def start_requests(self):
        for code in self.search_codes:
            yield Request(self.search_url % code, meta={'brand': 'SurfBoard', 'sku': code})

    def parse_reviews(self, response):
        product = response.meta['product']
        identifier = response.meta['identifier']
        json_body = json.loads(response.body)

        reviews = json_body['result']
        for review in reviews:
            review_loader = self.ReviewLoaderCls(item=Review(), response=response, date_format="%m/%d/%Y")
            parsed_review = self.parse_review(product['url'], review, review_loader)

            product['metadata']['reviews'].append(parsed_review)

        if len(reviews) == 100:
            offset = response.meta['offset'] + 100
            next_reviews = self._get_reviews_url(identifier, offset)
            request = Request(next_reviews, meta={'product': product, 'offset': offset, 'identifier': identifier},
                              callback=self.parse_reviews)
            yield request
        else:
            yield product

    def parse_review(self, product_url, review, review_loader):
        review_date = datetime.strptime(review['SubmissionTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        review_loader.add_value('date', review_date.strftime("%m/%d/%Y"))

        full_text = self.get_review_full_text(review)

        pros = review['Pros']
        cons = review['Cons']
        if pros:
            full_text += '\nPros: ' + ', '.join(pros)
        if cons:
            full_text += '\nCons: ' + ', '.join(cons)

        review_loader.add_value('full_text', full_text)
        rating = review['Rating']
        review_loader.add_value('rating', rating)
        review_loader.add_value('author_location', review['UserLocation'])
        review_loader.add_value('author', review['UserNickname'])
        review_loader.add_value('url', product_url)
        review = review_loader.load_item()
        return review

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        out_stock = bool(hxs.select('//div[@class="shipping"]//*[contains(text(), "not available")]'))

        for obj in super(TargetSpider, self).parse_product(response):
            if out_stock:
                if isinstance(obj, Request):
                    obj.meta['product']['stock'] = 0
                elif isinstance(obj, Product):
                    obj['stock'] = 0
            yield obj
