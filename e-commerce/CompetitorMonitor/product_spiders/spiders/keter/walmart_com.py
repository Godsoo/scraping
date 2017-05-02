# -*- coding: utf-8 -*-

import urlparse
import re

from product_spiders.spiders.siehunting.generic import GenericReviewSpider
import logging


from scrapy.http import Request, HtmlResponse
from scrapy.selector import HtmlXPathSelector

from product_spiders.spiders.keter.keteritems import KeterMeta, ReviewLoader, Review

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'


def get_reviews_url(product):
    url = product['url']
    productId = url.split('/')[-1].split('.')
    if productId:
        return 'http://walmart.ugc.bazaarvoice.com/1336a/%s/reviews.djs?format=embeddedhtml' % productId[0]
        # return 'http://reviews.walmart.com/1336/%s/reviews.htm' % productId[0]
    return None


def review_rating_extractor(review_box):
    url = review_box.select('.//div[@id="BVRRRatingOverall_Review_Display"]/div[@class="BVRRRatingNormalImage"]//div[@class="BVImgOrSprite"]//img/@alt').extract()
    if url:
        return url[0].split(" ")[0]
    return None


def sku_extractor(product_box):
    sku = product_box.select('.//div[@itemprop="description"]/div[2]/text()').extract()
    if sku:
        sku = sku[0].strip()
        if len(sku) > 20 or ' ' in sku:
            sku = None
    return sku

def xpath_select(hxs, selector):
    if not hxs: return []
    parts = selector.replace('//tbody', '/tbody').split('/tbody')
    if len(parts) == 1:
        return hxs.select(selector)
    current = hxs.select(parts[0])
    for s in parts[1:]:
        temp = current.select("./tbody")
        if temp:
            current = temp
        current = current.select("." + s)
    return current


class WalmartSpider(GenericReviewSpider):
    name = "keter-walmart.com"
    allowed_domains = ["walmart.com", "walmart.ugc.bazaarvoice.com"]
    start_urls = [
        'http://www.walmart.com/search/search-ng.do?ic=16_0&Find=Find&search_constraint=0&search_query=keter&_refineresult=true&cat_id=0',
        'http://www.walmart.com/search/search-ng.do?Find=Find&_refineresult=true&_ta=1&_tt=keter&search_constraint=0&search_query=keter&facet=brand%3AKeter',
        'http://www.walmart.com/search/search-ng.do?ic=16_0&Find=Find&search_constraint=0&search_query=SUNCAST&_refineresult=true&cat_id=0',
        'http://www.walmart.com/search/search-ng.do?Find=Find&_refineresult=true&_ta=1&_tt=sunca&search_constraint=0&search_query=suncast&facet=brand%3ASuncast||brand%3Asuncast',
        'http://www.walmart.com/search/search-ng.do?ic=16_0&Find=Find&search_constraint=0&search_query=rubbermaid&_refineresult=true&cat_id=0',
        'http://www.walmart.com/search/search-ng.do?Find=Find&_refineresult=true&_ta=1&_tt=rubbermaid&search_constraint=0&search_query=rubbermaid&facet=brand%3ARubbermaid',
        'http://www.walmart.com/search/search-ng.do?ic=16_0&Find=Find&search_constraint=0&search_query=lifetime&_refineresult=true&cat_id=0',
        'http://www.walmart.com/search/search-ng.do?Find=Find&_refineresult=true&ic=16_0&search_constraint=0&search_query=lifetime&facet=brand%3ALifetime',
        'http://www.walmart.com/search/search-ng.do?ic=16_0&Find=Find&search_constraint=0&search_query=step2&_refineresult=true&cat_id=0',
        'http://www.walmart.com/search/search-ng.do?Find=Find&_refineresult=true&_ta=1&_tt=step&search_constraint=0&search_query=step2&facet=brand%3AStep2||brand%3Astep2',
        'http://www.walmart.com/search/search-ng.do?ic=16_0&Find=Find&search_constraint=0&search_query=STERILITE&facet=brand%3ASterilite%7C%7Cbrand%3Asterilite&_refineresult=true&cat_id=0',
        'http://www.walmart.com/search/search-ng.do?Find=Find&_refineresult=true&_ta=1&_tt=sterili&search_constraint=0&search_query=sterilite&facet=brand%3ASTERILITE||brand%3ASterilite||brand%3Asterilite'
    ]

    PRODUCT_REVIEW_BOX = {}
    BRAND_GET_PARAM = 'search_query'
    NAVIGATION = ['//a[contains(@class, "prodLink")][1]/@href', '//div[@class="SPPagination"][1]//a/@href']

    PRODUCT_BOX = [
        # ('//div[@id="border"]/div', {'name': './/a[@class="prodLink ListItemLink"]/text()', 'url': './/a[@class="prodLink ListItemLink"]/@href', 'price': ['.//div[@class="camelPrice"]//span/text()']}),
        ('.', {'name': '//h1[@class="productTitle"]/text()',
               'price': ['//div[@id="WM_PRICE"]//span/text()',
                         '//div[@class="onlinePriceMP"]//span/text()',
                         '//div[contains(@class, "camelPrice")]//span/text()',
                         ],
               'sku': sku_extractor,
               'identifier': '//input[@name="product_id"]/@value',
               'image_url': '//*[@id="mainImage"]/@src',
               'category': '//*[@id="crumbs"]/li[1]/a/text()',
               'review_url': get_reviews_url}),
    ]

    PRODUCT_REVIEW_DATE_FORMAT = '%m/%d/%Y'
    PRODUCT_REVIEW_BOX = {'xpath': u'//div[starts-with(@id, "BVRRDisplayContentReviewID_")]', 'full_text': './/div[@class="BVRRReviewTextContainer"]//span/text()', 'date': u'.//span[contains(@class,"BVRRReviewDate")]/text()', 'rating': review_rating_extractor, 'next_url': '//a[@name="BV_TrackingTag_Review_Display_NextPage"]/@href'}

    def parse_product_reviews(self, response):

        for line in response.body.split('\n'):
            if line.startswith('var materials='):
                body = line.lstrip('var materials=').rstrip(',')
                break

        try:
            body = eval(body)
        except:
            logging.error('Failed to parse: ' + repr(response.body))
            body = ''

        # Emulate "normal" HTML response
        if body:
            body = ('<html><body>' +
                    '%s' +
                    '</body></html>') % (body['BVRRSourceID'].replace('\\/', '/'))

        response2 = HtmlResponse(url=response.url, body=body)
        response2.request = response.request



        hxs = HtmlXPathSelector(response2) if body else None
        base_url = self.get_base_url(response)
        product = response.meta['product']
        product['metadata'].setdefault('reviews', [])

        box_spec = self.PRODUCT_REVIEW_BOX or {}

        review_hxs = xpath_select(hxs, box_spec.get('xpath')) if 'xpath' in box_spec and box_spec.get('xpath') != "." else hxs

        for review_box in review_hxs:
            loader = ReviewLoader(item=Review(), selector=hxs, date_format=self.PRODUCT_REVIEW_DATE_FORMAT)
            loader.add_value('url', urlparse.urljoin(base_url, response.url))
            # review full text
            full_text_specs = box_spec.get('full_text', []) if hasattr(box_spec.get('full_text', []), 'append') else [box_spec['full_text']]
            full_text_parts = []
            for xpath in full_text_specs:
                items = xpath_select(review_box, xpath).extract() if not callable(xpath) else [xpath(hxs)]
                if any(items):
                    item_text = self.REVIEW_TEXT_JOIN.join([e.replace(u'\xa0', u' ').strip(self.REVIEW_TEXT_STRIP) for e in items])
                    full_text_parts.append(item_text)

            review_text = self.REVIEW_PARAGRAPH_JOIN.join(full_text_parts)
            loader.add_value('full_text', review_text)

            if box_spec.get('date'):
                date = review_box.select(box_spec.get('date')).extract() if not callable(box_spec.get('date')) else [box_spec['date'](review_box)]
                loader.add_value('date', date[0] if date else None)

            if box_spec.get('rating'):
                rating_text = review_box.select(box_spec.get('rating')).extract() if not callable(box_spec.get('rating')) else [box_spec['rating'](review_box)]
                loader.add_value('rating', rating_text[0] if rating_text else None)

            review = loader.load_item()
            if review.get('full_text') or review.get('date'):
                product['metadata']['reviews'].append(review)

        next_page = xpath_select(hxs, box_spec.get('next_url')).extract() if (box_spec.get('next_url') and not callable(box_spec['next_url'])) else [box_spec['next_url'](response, hxs)] if callable(box_spec.get('next_url')) else None
        next_page_url = urlparse.urljoin(base_url, next_page[0]) if any(next_page) else None

        if not next_page_url or next_page_url in self.visited_urls or not review_hxs:
            yield self.clean_product(product)
        else:
            self.visited_urls.add(next_page_url)
            yield Request(url=next_page_url, meta=dict(**response.meta), callback=self.parse_product_reviews)

    def visit_product_page(self, response, product):
        return True  # visit product page to have access to sku
