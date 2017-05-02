# -*- coding: utf-8 -*-

import os
import csv
import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from householditems import ReviewLoader, Review

HERE = os.path.abspath(os.path.dirname(__file__))


def review_rating_extractor(review_box):
        url = review_box.select('.//div[@id="BVRRRatingOverall_Review_Display"]/div[@class="BVRRRatingNormalImage"]//div[@class="BVImgOrSprite"]//img/@alt').extract()
        if url:
            return url[0].split(" ")[0]
        return None


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


class WalmartSpider(BaseSpider):
    name = 'householdessentials-walmart.com'
    allowed_domains = ['walmart.com', 'walmart.ugc.bazaarvoice.com']
    start_urls = ('http://www.walmart.com')

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

    rotate_agent = True

    def start_requests(self):
        # Parse default items and then start_urls
        yield Request('http://www.walmart.com', self.parse_default)

    def parse_default(self, response):
        with open(os.path.join(HERE, 'householdessentials_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row['Walmart #']
                if code != '#N/A':
                    yield Request('http://www.walmart.com/search/?query='+code,
                                  callback=self.parse, meta={'brand': row.get('Brand', ''),
                                                             'sku': row['Item Number']})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        real_crawl = response.meta.get('real_crawl', False)

        items = hxs.select('//div[@id="tile-container"]/div/a/@href').extract()
        for url in items:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

        next_pages = hxs.select('//a[contains(@class,"paginator-btn")]/@href').extract()
        if next_pages:
            for next_page in next_pages:
                yield Request(urljoin_rfc(base_url, next_page), meta=response.meta)

        if not items and not next_pages and real_crawl:
            self.errors.append('WARNING: No items => %s' % response.url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        if 'WALMART' not in ''.join(response.xpath('//div[contains(@class, "seller-info")]//span[@class="seller-walmart"]//b/text()').extract()).upper():
            return

        price = ''.join(hxs.select('//div[contains(@class, "js-product-offer-summary")]//div[contains(@class, "price-display")]//text()').extract())
        if not price:
            price = ''.join(response.xpath('//div[@itemprop="offers"]//div[@itemprop="price"][1]//text()').extract())
        if not price:
            price = ''.join(response.xpath('//span[contains(@class, "hide-content-m")]/span[@data-tl-id="Price-ProductOffer"]//text()').extract())
        # Some products are not available online and these have no price
        if price:
            stock_status = 1
            if 'out of stock' in price.lower():
                stock_status = 0

            product_name = filter(lambda x: bool(x), map(unicode.strip, hxs.select('//h1[contains(@itemprop, "name")]//text()').extract()))

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', product_name)
            loader.add_value('identifier', re.search(r'/(\d+)$', response.url).group(1))
            loader.add_value('sku', response.meta['sku'])
            loader.add_value('brand', response.meta['brand'])
            categories = hxs.select('//ol[contains(@class, "breadcrumb-list")]//li//a/span/text()').extract()
            categories = map(lambda x: x.strip(), categories)
            loader.add_value('category', categories)
            loader.add_value('url', response.url)
            loader.add_xpath('image_url', '//img[contains(@class, "js-product-primary-image")]/@src')

            loader.add_value('price', price)
            if not stock_status:
                loader.add_value('stock', 0)
            item = loader.load_item()
            item['metadata'] = {}

            yield Request(self._get_reviews_url(item, 1), meta={'product': item, 'page': 1}, callback=self.parse_product_reviews)

    def parse_special_price(self, response):
        data = json.loads(response.body)

        product = Product(response.meta['product'])
        for cart_item in data['items']:
            if str(cart_item['product_id']) == str(product['identifier']):
                product['price'] = extract_price(cart_item['subMapPrice'])

        yield Request(
            self._get_reviews_url(product, 1),
            meta={'product': product,
                  'page': 1},
            callback=self.parse_product_reviews)

    def parse_product_reviews(self, response):
        hxs = HtmlXPathSelector(response)

        product = response.meta['product']
        product['metadata'].setdefault('reviews', [])

        reviews = hxs.select(u'//div[@class="js-review-list"]/div[contains(@class, "customer-review")]')

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=hxs, date_format=self.PRODUCT_REVIEW_DATE_FORMAT)
            loader.add_value('url', response.url)

            review_text = ''

            title = review.select('.//div[contains(@class, "customer-review-title")]/text()').extract()
            if title:
                review_text += title[0].strip() + ' #&#&#&# '

            review_text += ''.join(review.select('.//div[@class="customer-review-text"]//text()').extract()).strip(" \r\n")
            review_text += ' #&#&#&# ' + ' '.join(filter(lambda s: s, map(unicode.strip, review.select('.//div[contains(@class, "customer-info")]//text()').extract()))).strip()
            loader.add_value('full_text', review_text)

            date = review.select('.//span[contains(@class, "customer-review-date")]/text()').extract()
            loader.add_value('date', date[0] if date else None)

            rating_text = review.select('.//div[contains(@class, "customer-stars")]/span[contains(@class, "visuallyhidden")]/text()').re(r'(\d+)')
            loader.add_value('rating', rating_text[0] if rating_text else None)

            review = loader.load_item()
            if review.get('full_text') or review.get('date'):
                product['metadata']['reviews'].append(review)

        page = response.meta['page'] + 1
        review_pages = hxs.select('//a[contains(@class, "js-pagination")]/@data-page').extract()

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
