# -*- coding: utf-8 -*-
from product_spiders.spiders.siehunting.generic import GenericReviewSpider

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'

import re

sku_re = re.compile('Model: \w+')


def sku_extractor(product_box):
    model = sku_re.findall("".join(product_box.select('//div[@id="product-tab1"]/text()').extract()).strip())
    if model:
        return model[0].split(": ")[-1]
    return None


class CostcoSpider(GenericReviewSpider):
    name = "keter-costco.com"
    allowed_domains = ["costco.com"]

    start_urls = [
        'http://www.costco.com/CatalogSearch?storeId=10301&catalogId=10701&langId=-1&keyword=Keter',
        'http://www.costco.com/CatalogSearch?storeId=10301&catalogId=10701&langId=-1&keyword=SUNCAST',
        'http://www.costco.com/CatalogSearch?storeId=10301&catalogId=10701&langId=-1&keyword=RUBBERMAID',
        'http://www.costco.com/CatalogSearch?storeId=10301&catalogId=10701&langId=-1&keyword=LIFETIME',
        'http://www.costco.com/CatalogSearch?storeId=10301&catalogId=10701&langId=-1&keyword=STEP2',
        'http://www.costco.com/CatalogSearch?storeId=10301&catalogId=10701&langId=-1&keyword=STERILITE',
    ]

    BRAND_GET_PARAM = "keyword"

    NAVIGATION = ['//div[@id="secondary_content_wrapper"]/div[@class="box-747"]/div[@class="h2-line"]//div[@class="pagination"]//a/@href',
                  '//div[@class="grid-4col"]//a/@href']

    PRODUCT_BOX = [
        ('.', {'name': '//div[@class="top_review_panel"]//h1/text()',
               'price': '//span[@class="currency"]/text()',
               'sku': sku_extractor,
               'image_url': '//*[@id="large_images"]/li/img/@src',
               'category': '//*[@id="breadcrumbs"]/li[2]/a/text()',
               'identifier': '//form[@id="ProductForm"]//input[@name="addedItem"]/@value',
               'review_url': '//iframe[@id="BVFrame"]/@src'})
    ]

    PRODUCT_REVIEW_DATE_FORMAT = '%B %d, %Y'
    PRODUCT_REVIEW_BOX = {'xpath': '//div[@id="BVRRDisplayContentBodyID"]/div', 'full_text': ['.//div[@class="BVRRReviewProsContainer"]//span/text()', './/div[@class="BVRRReviewConsContainer"]//span/text()', './/span[@class="BVRRReviewText"]/text()'], 'date': './/div[@class="BVRRReviewDateContainer"]//span[@class="BVRRValue BVRRReviewDate"]/text()', 'rating': './/div[@class="BVRRRatingNormalOutOf"]//span[1]/text()', 'next_url': '//a[@name="BV_TrackingTag_Review_Display_NextPage"]/@href'}

    REVIEW_PARAGRAPH_JOIN = "\r\n"
    REVIEW_TEXT_STRIP = '\r\n'
    REVIEW_TEXT_JOIN = ""

    def keep_product(self, response, product_box, product):
        keep = super(CostcoSpider, self).keep_product(response, product_box, product)
        if keep:
            keep = product['identifier'] is not None and str(product['identifier']).strip() != ''
        return keep
