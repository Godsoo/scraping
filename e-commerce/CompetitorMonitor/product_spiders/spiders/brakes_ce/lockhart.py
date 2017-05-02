# -*- coding: utf-8 -*-
"""
This spider was copied from the Alliance Online account, it's set to extract all items.
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4843-brakes-ce-|-lockhart--amp--nisbets-|-secondary-spiders/details#
"""

import os
import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log
from scrapy.contrib.loader.processor import TakeFirst, Compose
from decimal import Decimal
import urlparse

from product_spiders.items import Product, ProductLoader


PARAM_BRAND_NAME = '05000-GeneralBrand'


def extract_price(text):
    price_str = re.sub(r'(?u)(\d),(\d)', '\\1\\2', text)
    match_obj = re.search(r'([.0-9]+)', price_str)
    if match_obj:
        return match_obj.group(1)
    else:
        log.msg("Price could not be extracted from %r" % text, level=log.DEBUG)
        log.msg("After removing comma: %r" % price_str, level=log.DEBUG)
        log.msg("After parsing number: %r" % match_obj, level=log.DEBUG)
        return 0


def get_brand_from_url(url):
    parsed_url = urlparse.urlparse(url)
    query_string_dict = dict(urlparse.parse_qsl(parsed_url.query))
    return query_string_dict.get(PARAM_BRAND_NAME)


def get_full_url(response, url):
    return urljoin_rfc(get_base_url(response), url)


class LockhartCatering(BaseSpider):
    name = 'brakes_ce-lockhartcatering.co.uk'
    allowed_domains = ['www.lockhartcatering.co.uk']
    start_urls = ('http://www.lockhartcatering.co.uk/sitemap/',)
    # start_urls = ('http://www.lockhartcatering.co.uk/bunzlsitemap.xml', )
    download_delay = 1.0
    retry_count = 15

    def retry(self, response, callback):
        meta = response.meta.copy()
        callbackname = callback.__name__
        key = 'retry-%s' % callbackname
        meta[key] = meta.get(key, 0)
        if meta[key] < self.retry_count:
            meta[key] += 1
            meta['recache'] = True
            self.log('RETRY %s %d => %s' % (callbackname, meta[key], response.request.url))
            return Request(response.request.url, meta=meta, callback=callback)
        else:
            self.log('RETRY Exhausted for %s' % response.request.url)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@class="trunk" and div/h2/a]/div[position()<(last()-4)]/div/div/a/@href').extract()
        # categories = hxs.select('//url/loc/text()').extract()

        for category_url in categories:
            yield Request(get_full_url(response, category_url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brand_urls = hxs.select('//span[@id="05000-GeneralBrand_facetValues"]/parent::div/following-sibling::li//a[@class="selectable"]/@href').extract()

        self.log("Brand urls%s" % " found" if brand_urls else "")
        if brand_urls:
            for brand_url in brand_urls:
                yield Request(get_full_url(response, "%s&viewAll=true" % brand_url),
                              callback=self.parse_brand_list)
        else:
            yield Request(get_full_url(response, "?viewAll=true"), callback=self.parse_brand_list)

        new_products = hxs.select('//a[child::span[@class="facetProd" and text()="New"]]/@href').extract()
        if new_products:
            yield Request(get_full_url(response, "%s&viewAll=true" % new_products[0]), callback=self.parse_brand_list)

        price_ranges = hxs.select('//span[@id="price_facetValues"]/../following-sibling::li//a/@href').extract()
        for price_range in price_ranges:
            yield Request(get_full_url(response, "%s&viewAll=true" % price_range), callback=self.parse_brand_list)

        for url in hxs.select('//div[@class="categoryTree_main"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url).split(';jsessionid')[0], callback=self.parse_category)

    def parse_brand_list(self, response):
        hxs = HtmlXPathSelector(response)

        # products
        product_items = hxs.select('//div[@class="productGrid"]/ul/li/div[@class="item"]')
        category_items = hxs.select('//h1[@class="categoryLandingPageTitle_heading"]/a/text()').extract()
        category = category_items[0] if category_items else ''
        brand_name = get_brand_from_url(response.url)

        def get_full_image_url(url):
            return get_full_url(response, url)

        for product_item in product_items:

            image_url = product_item.select(u'div[@class="prodimg"]/a/img/@src').extract()
            if image_url:
                image_url = get_full_url(response, image_url[0])

            ploadr = ProductLoader(item=Product(), selector=product_item, response=response)

            ploadr.add_xpath('name',
                             'div[@class="prodname"]/a/text()',
                             TakeFirst(), Compose(unicode.strip))
            ploadr.add_xpath('url', 'div[@class="prodname"]/a/@href',
                             TakeFirst(), Compose(unicode.strip), Compose(get_full_image_url))
            ploadr.add_value('category', category)
            ploadr.add_value('image_url', image_url)

            price = ploadr.get_xpath('div[@class="proddetails"]//div[@class="prodnowprice"]/span/text()',
                                     TakeFirst(), Compose(extract_price))
            price_excl_vat = Decimal(price)

            ploadr.add_value('price', price_excl_vat)

            ploadr.add_value('shipping_cost', Decimal('5.00') if price_excl_vat < 50 else Decimal('0.0'))
            ploadr.add_xpath('sku',
                             'div[@class="proddetails"]//div[@class="proditemcode"]/a/span/following-sibling::text()',
                             TakeFirst(), Compose(unicode.strip))

            ploadr.add_value('identifier', ploadr.get_output_value('sku'))
            stock_info = product_item.select(u'div[@class="proddetails"]/div/div/span[contains(@class, "instock")]/@class').extract()
            buy_button = product_item.select(u'div[@class="proddetails"]/div[@class="prodquickbuy"]/a[@class="primaryBtn"]').extract()

            ploadr.add_value('brand', brand_name)

            ploadr.add_value('stock', 1 if stock_info or buy_button else 0)

            item = ploadr.load_item()

            tmp = ''.join(product_item.select("//div[@class='proditemcode']//text()").extract())
            item['metadata'] = {'product_code': tmp.split(':')[-1].strip()}

            if not ploadr.get_output_value('brand'):
                yield Request(item['url'], meta={'item': item}, callback=self.parse_brand)
            else:
                yield item

    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response)
        item = response.meta.get('item')
        brand = hxs.select('//div[@class="productDetail_tab_content"]//p/text()').re('Brand: (.*)')
        if brand:
            item['brand'] = brand[0].strip()
        yield item

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        name = hxs.select('//div[@class="productDetail_name_and_description"]/h1/text()')[0].extract().strip()
        sku = hxs.select('//input[@name="productCode"]/@value')[0].extract()
        image_url = hxs.select('//img[@id="zoom"]/@src').extract()
        category = hxs.select('//div[@id="breadcrumbs"]/a[not(@class)]/text()').extract()
        brand = hxs.select('//div[@class="productDetail_tab_content"]//p/text()').re('Brand: (.*)')
        price = hxs.select('//div[@class="productDetail_main_pricelist"]/span[@id="now_price"]/text()')
        if not price:
            price = hxs.select('//div[@class="productDetail_main_pricelist"]/div[@id="now_price"]/text()')
        price = price.re('[\.\d,]+')[0].strip().replace(',', '') if price else '0.00'
        stock = hxs.select('//input[@class="primaryBasket"]').extract()
        price_excl_vat = Decimal(price)

        ploadr = ProductLoader(item=Product(), response=response)
        ploadr.add_value('name', name)
        ploadr.add_value('url', response.url)
        if image_url:
            ploadr.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))
        ploadr.add_value('sku', sku)
        ploadr.add_value('identifier', ploadr.get_output_value('sku'))
        ploadr.add_value('price', price_excl_vat)
        if category:
            ploadr.add_value('category', category[-1])
        if brand:
            ploadr.add_value('brand', brand[0].strip())
        ploadr.add_value('shipping_cost', Decimal('5.00') if price_excl_vat < 50 else Decimal('0.0'))
        ploadr.add_value('stock', 1 if stock else 0)
        item = ploadr.load_item()

        tmp = hxs.select("//div[@class='productDetail_item_code']/text()").extract()
        item['metadata'] = {'product_code': tmp[0].split(':')[-1].strip()}

        yield item
