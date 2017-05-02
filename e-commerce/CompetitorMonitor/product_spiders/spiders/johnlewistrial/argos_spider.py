import re

from datetime import datetime
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.item import Item, Field
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from decimal import Decimal
from product_spiders.items import (Product, ProductLoaderWithNameStrip as ProductLoader)
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst, Identity
from scrapy.contrib.loader import XPathItemLoader
from scrapy.utils.markup import remove_entities
from product_spiders.utils import extract_price
import logging

from johnlewisitems import JohnLewisMeta, Review, ReviewLoader


class ArgosCoUKKeterSpider(BaseSpider):
    name = 'johnlewis-trial-argos.co.uk'
    allowed_domains = ['argos.co.uk', 'argos.ugc.bazaarvoice.com']
    start_urls = [
        'http://www.argos.co.uk/static/Browse/ID72/33008255/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7Ccat_33005908%7CLarge+kitchen+appliances%7C33008255.htm',
        'http://www.argos.co.uk/static/Browse/ID72/33007917/c_1/1%7Ccategory_root%7CHome+and+garden%7C33005908/c_2/2%7Ccat_33005908%7CKitchen+electricals%7C33007917.htm',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//ul[@id="categoryList"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url))

        for url in hxs.select('//a[@class="page"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url))

#        for url in hxs.select('//div[@class="product"]//a/@href|//li[contains(@class,"item")]//a/@href').extract():
        for url in hxs.select('//a[@id="optimiseProductURL"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product,
                    meta={'category': ' > '.join([x.split('|')[2].replace('+', ' ') for x in hxs.select('//form[@id="refineform"]//input[starts-with(@name,"c_")]/@value').extract()])})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        l = ProductLoader(item=Product(), response=response)
        l.add_xpath('name', '//div[@id="pdpProduct"]/h1//text()')
        l.add_value('url', response.url) 
        l.add_xpath('price', '//span[@class="price"]//text()')
        l.add_value('sku', (''.join(hxs.select('//li[starts-with(text(),"EAN:")]/text()').extract())).split(':')[-1].replace('.', ''))
        l.add_xpath('identifier', '//div[@id="stkDetailsContainer"]//input[@name="partNumber"]/@value')
        image_url = hxs.select('//img[@id="mainimage"]/@src').extract()
        if image_url:
            l.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))
        l.add_xpath('shipping_cost', '//strong[contains(text(), "Delivery")]/text()')
        l.add_value('brand', (''.join(hxs.select('//div[@id="pdpProduct"]/h1//text()').extract())).split()[0])
        l.add_value('category', response.meta.get('category'))
        if l.get_output_value('price') > 0:
            l.add_value('stock','1')
        item = l.load_item()

        metadata = JohnLewisMeta()
        metadata['promotion'] = ''.join(hxs.select('normalize-space(//p[@class="saving"]/text())').extract())
        metadata['reviews'] = []
        item['metadata'] = metadata

        reviews_url = 'http://argos.ugc.bazaarvoice.com/1493-en_gb/%s/reviews.djs?format=embeddedhtml'
        # part_number = hxs.select(u'//form/input[@name="partNumber"]/@value').extract()[0]
        part_number = re.search(r'/partNumber/(\d+)', response.url).group(1)
        yield Request(reviews_url % part_number, callback=self.parse_review_page, meta={'product': item})

    def parse_review_page(self, response):
        item_ = response.meta.get('product', '')
        hxs = HtmlXPathSelector(text=self._extract_html(response))
        reviews = hxs.select('//div[@class="BVRRReviewDisplayStyle5"]')
        for review in reviews:
            l = ReviewLoader(item=Review(), response=response, date_format='%m/%d/%Y')
            rating = review.select(".//span[contains(@class,'BVRRRatingNumber')]/text()").extract()[0]
            date = review.select(".//span[contains(@class,'BVRRValue BVRRReviewDate')]/text()").extract()[0]
            review = review.select(".//span[contains(@class,'BVRRReviewText')]/text()")[1].extract()

            l.add_value('rating', rating)
            l.add_value('url', response.url)
            l.add_value('date', datetime.strptime(date, '%d %B %Y').strftime('%m/%d/%Y'))
            l.add_value('full_text', review)
            item_['metadata']['reviews'].append(l.load_item())

        next = hxs.select('//span[@class="BVRRPageLink BVRRNextPage"]/a/@data-bvjsref').extract()
        if next:
            yield Request(next[0], callback=self.parse_review_page, meta={'product': item_})
        else:
            yield item_

    def _extract_html(self, response):
        review_html = ''
        for line in response.body.split('\n'):
            if 'var materials=' in line:
                review_html = line.split('"BVRRSecondaryRatingSummarySourceID":" ')[-1].split('\n}')[0].replace('\\', '')
        return review_html
