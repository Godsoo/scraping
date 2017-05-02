# -*- coding: utf-8 -*-

import re
import os
import shutil
import json
from datetime import datetime
from scrapy import Spider, Request
from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst
from scrapy.utils.markup import remove_entities
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)


class LegoUSAMeta(Item):
    reviews = Field()


class Review(Item):
    date = Field()
    rating = Field()
    full_text = Field()
    url = Field()
    product_url = Field()
    sku = Field()


def extract_date(s, loader_context):
    date_format = loader_context['date_format']
    d = datetime.strptime(s, date_format)
    return d.strftime('%m/%d/%Y')


def extract_rating(s):
    r = re.search('(\d+)', s)
    if r:
        return int(r.groups()[0])


class ReviewLoader(XPathItemLoader):
    date_in = MapCompose(unicode, unicode.strip, extract_date, date_format='%m/%d/%Y')
    date_out = TakeFirst()

    rating_in = MapCompose(unicode, extract_rating)
    rating_out = TakeFirst()

    full_text_in = MapCompose(unicode, unicode.strip, remove_entities)
    full_text_out = Join()

    url_in = MapCompose(unicode, unicode.strip)
    url_out = TakeFirst()


def review_rating_extractor(review_box):
        url = review_box.xpath('.//div[@id="BVRRRatingOverall_Review_Display"]/div[@class="BVRRRatingNormalImage"]//div[@class="BVImgOrSprite"]//img/@alt').extract()
        if url:
            return url[0].split(" ")[0]
        return None


class WalmartSpider(Spider):
    HERE = os.path.abspath(os.path.dirname(__file__))
    allowed_domains = ['walmart.com', 'walmart.ugc.bazaarvoice.com']

    PRODUCT_REVIEW_DATE_FORMAT = '%m/%d/%Y'
    PRODUCT_REVIEW_BOX = {
        'xpath': '//div[@class="js-review-list"]/div[contains(@class, "customer-review")]',
        'full_text': ['.//div[@class="customer-review-text"]//text()'],
        'date': './/span[contains(@class,"BVRRReviewDate")]/text()',
        'rating': review_rating_extractor,
        'next_url': '//a[@name="BV_TrackingTag_Review_Display_NextPage"]/@href',
    }

    REVIEW_TEXT_STRIP = '" \r\n"'
    REVIEW_TEXT_JOIN = " "
    REVIEW_PARAGRAPH_JOIN = ". "
    enable_map = False

    def __init__(self, *args, **kwargs):
        super(WalmartSpider, self).__init__(*args, **kwargs)

        self.errors = []
        self.map_screenshot_html_files = {}

    def spider_closed(self, spider):
        shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(self.HERE, 'walmart_products.csv'))

    def parse_product(self, response):
        try:
            pjs_data = json.loads(response.xpath('//script[@id="tb-djs-wml-base"]/text()').extract()[0].strip())
            price = str(pjs_data['adContextJSON']['price'])
        except:
            price = None

        if not price:
            price = ''.join(response.xpath('//div[contains(@class, "js-product-offer-summary")]'
                                           '//div[contains(@class, "price-display")]//text()').extract())
        if not price:
            price = ''.join(response.xpath('//div[contains(@class, "PricingInfo clearfix")]'
                                           '//span[contains(@class, "clearfix camelPrice")]//text()').extract())

        # Some products are not available online and these have no price
        if not price:
            self.log('No price found {}'.format(response.url))

        if price:
            stock_status = 1
            if 'out of stock' in price.lower():
                stock_status = 0
            sku = response.xpath('//td[contains(text(), "Model No")]/following-sibling::td/text()').extract()
            if not sku:
                sku = response.xpath('//td[contains(text(), "Model:")]/following-sibling::td/text()').extract()
            if not sku:
                # Retry
                retry = int(response.meta.get('retry', 0))
                if retry < 5:
                    retry += 1
                    meta = response.meta.copy()
                    meta['retry'] = retry
                    yield Request(response.url, callback=self.parse_product, meta=meta, dont_filter=True)
                else:
                    self.log('NO SKU => %s' % response.url)
                return
            loader = ProductLoader(item=Product(), response=response)
            loader.add_xpath('name', '//h1[@itemprop = "name"]//text()')
            loader.add_value('identifier', re.search(r'/(\d+)\[?|$]', response.url).group(1))
            loader.add_value('sku', sku[0].strip())
            if response.meta.get('brand'):
                loader.add_value('brand', response.meta.get('brand'))
            else:
                loader.add_value('brand', 'LEGO')
            loader.add_xpath('category', '//ol[contains(@class, "breadcrumb-list")]//li[last()]//a/span/text()')
            loader.add_value('url', response.url)
            loader.add_xpath('image_url', '//img[contains(@id, "mainImage") or contains(@class, "product-primary-image")]/@src')

            loader.add_value('price', price)
            if not stock_status:
                loader.add_value('stock', 0)
            item = loader.load_item()
            item['metadata'] = {}

            if self.enable_map:
                self._save_html_response(response, item['identifier'])

            yield Request(self._get_reviews_url(item, 1), meta={'product': item, 'page': 1}, callback=self.parse_product_reviews)

    def parse_product_reviews(self, response):
        product = response.meta['product']
        product['metadata'].setdefault('reviews', [])

        reviews = response.xpath(u'//div[@class="js-review-list"]/div[contains(@class, "customer-review")]')

        for review in reviews:
            loader = ReviewLoader(item=Review(), response=response, date_format=self.PRODUCT_REVIEW_DATE_FORMAT)
            loader.add_value('product_url', product['url'])
            loader.add_value('url', response.url)
            loader.add_value('sku', product['sku'])

            review_text = ''

            title = review.xpath('.//div[contains(@class, "customer-review-title")]/text()').extract()
            if title:
                review_text += title[0].strip() + ' #&#&#&# '

            review_text += ''.join(review.xpath('.//div[@class="customer-review-text"]//text()').extract()).strip(" \r\n")
            review_text += ' #&#&#&# ' + ' '.join(filter(lambda s: s, map(unicode.strip, review.xpath('.//div[contains(@class, "customer-info")]//text()').extract()))).strip()
            loader.add_value('full_text', review_text)

            date = review.xpath('.//span[contains(@class, "customer-review-date")]/text()').extract()
            loader.add_value('date', date[0] if date else None)

            rating_text = review.xpath('.//div[contains(@class, "customer-stars")]/span[contains(@class, "visuallyhidden")]/text()').re(r'(\d+)')
            loader.add_value('rating', rating_text[0] if rating_text else None)

            review = loader.load_item()
            if review.get('full_text') or review.get('date'):
                product['metadata']['reviews'].append(review)

        page = response.meta['page'] + 1
        review_pages = response.xpath('//a[contains(@class, "js-pagination")]/@data-page').extract()

        if not reviews or str(page) not in review_pages:
            yield product
        else:
            meta = response.meta.copy()
            meta['page'] = page
            yield Request(url=self._get_reviews_url(product, page), meta=meta, callback=self.parse_product_reviews)

    def _get_reviews_url(self, product, page):
        url = product['url']
        productId = url.split('/')[-1].split('.')
        if productId:
            return 'https://www.walmart.com/reviews/product/%s?page=%s' % (productId[0], page)
        return None

    def _save_html_response(self, response, identifier):
        filename = os.path.join(self.HERE, 'walmart_%s.html' % identifier)
        with open(filename, 'w') as f_html:
            f_html.write(response.body)
        self.map_screenshot_html_files[identifier] = filename
