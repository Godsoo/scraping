# -*- coding: utf-8 -*-

from product_spiders.spiders.siehunting.generic import GenericReviewSpider

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'


def name_extractor(product_box):
    product_name = product_box.select('//h1[@class="title"]/text()').extract()
    if product_name:
        name = " ".join([n.strip(' \r\n\t') for n in product_name if n.strip(' \r\n\t')])
        return ",".join(name.split(',')[:-1]) if "," in name else name
    return None


def sku_extractor(product_box):
    product_name = product_box.select('//h1[@class="title"]/text()').extract()
    if product_name:
        name = " ".join([n.strip(' \r\n\t') for n in product_name if n.strip(' \r\n\t')])
        return name.split(',')[-1].split("#")[-1].strip() if "," in name else None
    return None


def identifier_extractor(product_box):
    identifier = product_box.select('//*[contains(@id,"quantity_")]/@id').extract()
    if identifier:
        identifier = identifier[0].split('_')
        if len(identifier) > 1:
            return identifier[1].strip()
    return None


def category_extractor(product_box):
    try:
        return product_box.select('//script[@type="text/javascript"]').re(r'category_\dz.*:.*\["(.*)"]').pop()
    except:
        return None


class NorthernToolSpider(GenericReviewSpider):
    name = "keter-northerntool.com"
    allowed_domains = ["northerntool.com"]

    start_urls = [
        'http://www.northerntool.com/shop/tools/NTESearch?storeId=6970&Ntt=Keter',
        'http://www.northerntool.com/shop/tools/NTESearch?storeId=6970&Ntt=SUNCAST',
        'http://www.northerntool.com/shop/tools/NTESearch?storeId=6970&Ntt=RUBBERMAID',
        'http://www.northerntool.com/shop/tools/NTESearch?storeId=6970&Ntt=LIFETIME',
        'http://www.northerntool.com/shop/tools/NTESearch?storeId=6970&Ntt=STEP2',
        'http://www.northerntool.com/shop/tools/NTESearch?storeId=6970&Ntt=STERILITE',
    ]
    BRAND_GET_PARAM = 'Ntt'

    NAVIGATION = ['//div[@id="content"]/div[@class="grid960_5"]/div[2]/div[4]//div[@class="resultSet"]//ul[@class="pagination"]//a/@href',
                  '//div[@id="content"]/div[@class="grid960_5"]/div[2]//a/@href',
                  '//div[@class="prod-description"]/div[@class="title"]/a/@href']

    PRODUCT_BOX = [
        # ('.', {'name': '//h1[@class="title"]/text()', 'price': ['//div[@id="WC_CachedProductOnlyDisplay_div_4"]//div[@class="sale-price"]/text()', '//div[@id="WC_CachedProductOnlyDisplay_div_4"]//div[@class="only-price"]/text()'], 'review_url': '//iframe[@id="BVFrame"]/@src'})
        ('.', {'name': name_extractor,
               'sku': sku_extractor,
               'image_url': '//img[@id="main-image"]/@src',
               'category': category_extractor,
               'identifier': identifier_extractor,
               'price': ['//div[@id="WC_CachedProductOnlyDisplay_div_4"]//div[@class="sale-price"]/text()',
                         '//div[@id="WC_CachedProductOnlyDisplay_div_4"]//div[@class="only-price"]//text()'],
               'review_url': '//iframe[@id="BVFrame"]/@src'})
    ]

    PRODUCT_REVIEW_DATE_FORMAT = '%B %d, %Y'
    PRODUCT_REVIEW_BOX = {'xpath': '//div[@id="BVRRDisplayContentBodyID"]/div',
                          'full_text': './/span[@class="BVRRReviewText"]/text()',
                          'date': './/div[@class="BVRRReviewDateContainer"]//span[@class="BVRRValue BVRRReviewDate"]/text()',
                          'rating': './/div[@class="BVRRRatingNormalOutOf"]//span[1]/text()',
                          'next_url': '//a[text() = "Next Page"]/@href'}
