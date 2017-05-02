# -*- coding: utf-8 -*-

import urlparse

from product_spiders.spiders.siehunting.generic import GenericReviewSpider
import re

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'

digits = re.compile(r"\d+")


def get_reviews_url(product):
    url = product['url']
    productId = digits.findall(url.split('/')[-1])
    if productId:
        return 'http://www.buylifetime.com/productreviews/getreviews?id=%s&page=1&sort=0' % productId[0]
    return None


def get_next_reviews_url(response, hxs=None):
    url = response.url
    parsed = urlparse.urlparse(url)
    params = urlparse.parse_qs(parsed.query)
    page = params.get('page')
    productId = params.get("id")
    if productId and page:
        return 'http://www.buylifetime.com/productreviews/getreviews?id=%s&page=%s&sort=0' % \
               (productId[0], int(page[0]) + 1)
    return None


def identifier_extractor(product_box):
    identifier = product_box.select('//select[@id="productIdList"]/option[@selected="selected"]/@value').extract()
    if not identifier:
        identifier = product_box.select('//select[@id="packquantity"]/option[@selected="selected"]/@value').extract()
        if not identifier:
            return None
    return identifier[0].strip()


def price_extractor(hxs, name):
    price = hxs.select('//select[@id="productIdList"]/option[@selected="selected"]/text()').re(r'(\$[0-9,]+(\.[0-9]{2})?)')
    if not price:
        price = hxs.select('//select[@id="packquantity"]/option[@selected="selected"]/text()').re(r'(\$[0-9,]+(\.[0-9]{2})?)')
        if not price:
            return None
    return price[0]


class BuyLifetimeSpider(GenericReviewSpider):
    name = "keter-buylifetime.com"
    allowed_domais = ["buylifetime.com"]

    start_urls = [
        "http://www.buylifetime.com/Products/BLT/outdoorSheds/Default.aspx",
        "http://www.buylifetime.com/Products/BLT/outdoorProducts/Default.aspx"
    ]

    BRAND_GET_PARAM = lambda e: "Lifetime"

    NAVIGATION = [
        '//ul[@id="category-list"]//a/@href', '//ul[@id="product-list"]//@href'
    ]

    PRODUCT_BOX = [
        ('.', {'name': '//h1[@id="product-header"]/text()',
               'price': price_extractor,
               'sku': '//div[@id="specifications"]//table//th[contains(text(), "Model")]//..//td/text()',
               'image_url': '//img[@id="product-image"]/@src',
               'identifier': identifier_extractor,
               'category': '//*[@id="breadcrumbs"]/a[2]/text()',
               'review_url': get_reviews_url})
    ]

    PRODUCT_REVIEW_DATE_FORMAT = '%m/%d/%Y'
    PRODUCT_REVIEW_BOX = {'xpath': '//body//div',
                          'full_text': './/p[@class="summary reviewComments"]/text()',
                          'date': './/span[@itemprop="datePublished"]/text()',
                          'rating': './/span[@class="rating-stars"]//span[@itemprop="ratingValue"]/text()',
                          'next_url': get_next_reviews_url}