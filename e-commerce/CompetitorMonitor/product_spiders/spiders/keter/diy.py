import urllib
import logging
from decimal import Decimal

from scrapy import log
from scrapy.item import Item, Field
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader
from scrapy.contrib.loader.processor import MapCompose, TakeFirst

class DiyComSpider(BaseSpider):
    name = 'keter-diy.com'
    allowed_domains = ['diy.com']
    # This is actual URL used by AJAX-based search
    # FIXME: currently limited to 1000 items
    search_url = 'http://search.diy.com/search?cnt=1000&ts=ajax&w='
    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

    def start_requests(self):
        for brand in ('Keter', 'SUNCAST', 'RUBBERMAID', 'LIFETIME', 'STEP 2', 'STERILITE'):
            yield Request(self.search_url + urllib.quote_plus(brand),
                    meta={'brand': brand},
                    callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        items = hxs.select(u'//div[@class="sli_grid_informationBlock"]/a/@href').extract()
        for item in items:
            yield Request(item, meta=response.meta, callback=self.parse_item)

    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)

        # Ensure the search matched brand, not some part of name or description
        #brand = hxs.select(u'//p/strong[contains(text(),"Brand:")]/../text()').extract()
        #brand = brand and brand[0].strip().lower()
        #if response.meta['brand'].lower() != brand:
        #    logging.warning('Brand [%s] not equal to search result brand [%s] [%s]' % (
        #                response.meta['brand'], brand, response.url))
        #    return
        brand = response.meta['brand'].lower()

        #in_stock = hxs.select(u'//p[@class="inStock"]/text()').extract()
        # FIXME: not sure "in stock" check is required
        #if not in_stock or in_stock[0] not in [u'In stock', u'Available for reserve & collect']:
        #    logging.warning('Skip [%s] because not in stock (%s)' % (response.url, in_stock))
        #    return


        # name = hxs.select('//div[@class="productInfo"]/h1/text()').extract()
        # if not name:
        #     name = hxs.select('//span[@id="btAsinTitle"]/text()').extract()
        name = hxs.select('//div[contains(@class,"product_page")]//dt/span/text()').extract()
        if not name:
            name = hxs.select('//title/text()').extract()

        if brand not in name[0].lower():
            logging.warning('Brand [%s] not found in product name [%s] [%s]' % (
                        brand, name[0], response.url))
            return

        product_loader = ProductLoader(item=Product(), response=response)

        product_loader.add_value('name', name[0])

        # price = hxs.select('//span[@class="onlyPrice"]/text()').extract()[0]
        price = hxs.select('//ul[contains(@class,"item_price")]/li/text()').extract()[0]
        price = price.replace('Only \u00a3', '')
        product_loader.add_value('price', price)

        # sku = hxs.select( '//p[@class="ean"]/text()').extract()[0]
        sku = hxs.select( '//dd[contains(text(),"EAN:")]/text()').extract()[0]
        sku = sku.replace('EAN: ', '')
        product_loader.add_value('sku', sku)
        product_loader.add_value('identifier', sku)

        product_loader.add_value('url', response.url)

        # printable_review_url = hxs.select(u'//div[@id="BVSVPLinkContainer"]/a/@href').extract()[0]
        printable_review_url = hxs.select(u'//iframe[@id="BVFrame"]/@src').extract()[0].replace('?format=embedded', '')
        product_loader.add_value('brand', brand.strip().lower())
        product = product_loader.load_item()

        metadata = KeterMeta()
        metadata['brand'] = brand.strip().lower()

        metadata['reviews'] = []
        product['metadata'] = metadata

        #yield product_loader.load_item()
        yield Request(printable_review_url, 
                       meta={'product': product},
                       callback=self.parse_review)

    def parse_review(self, response):
        hxs = HtmlXPathSelector(response)

        product = response.meta['product']
        for review in hxs.select(u'//div[starts-with(@id, "BVRRDisplayContentReviewID_")]'):
            review_loader = ReviewLoader(item=Review(), selector=review, date_format='%d/%m/%Y')
            review_loader.add_value('date', review.select(u'.//span[contains(@class,"BVRRReviewDate")]/text()').extract()[1])

            title = review.select(u'.//span[contains(@class,"BVRRReviewTitle")]/text()').extract()
            text = ' '.join(review.select(u'.//span[contains(@class,"BVRRReviewText")]/text()').extract())

            if title:
                full_text = title[0] + '\n' + text
            else:
                full_text = text
            review_loader.add_value('full_text', full_text)

            # Contains text "x out of 5", grab first symbol
            review_loader.add_value('rating', review.select(u'.//img[@class = "BVImgOrSprite"]/@title').extract()[0][:1])

            review_loader.add_value('url', response.url)

            product['metadata']['reviews'].append(review_loader.load_item())

        yield product

