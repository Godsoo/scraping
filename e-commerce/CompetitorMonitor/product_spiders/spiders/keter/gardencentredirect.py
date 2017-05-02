import re
import os
from HTMLParser import HTMLParser

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
from scrapy import log

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class GardenCentreDirectSpider(BaseSpider):
    name = 'gardencentredirect.co.uk'
    allowed_domains = ['gardencentredirect.co.uk']
    start_urls = ('http://gardencentredirect.co.uk',)

    def start_requests(self):
        brands = ['Keter', 'Suncast']
        search_url = u'http://www.gardencentredirect.co.uk/Search?q=%(brand)s&x=0&y=0'
        # brands = ({'url': u'http://www.gardencentredirect.co.uk/KeterUK', 'name': u'Keter'},
                  # {'url': u'http://www.gardencentredirect.co.uk/Suncast', 'name': u'Suncast'})
        for brand in brands:
            # yield Request(brand['url'], meta={'brand': brand['name']}, callback=self.parse_brand)
            yield Request(search_url % {'brand': brand}, meta={'brand': brand})

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        next_page = hxs.select(u'//a[text()="Next"]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, meta=response.meta)

        products = set(hxs.select(u'//a[@class="view-product-button"]/@href').extract())
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

    def parse_brand(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        products = set(hxs.select(u'//a[child::input[@class="view-product"]]/@href').extract())
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        category = hxs.select('//ul[@id="breadcrumbs"]/li/a/text()').extract()[-1]
        identifier = hxs.select('//input[@id="prodID"]/@value').extract()[0]
        image_url = urljoin_rfc(get_base_url(response), hxs.select('//img[@class="Product-Main-Image"]/@src').extract()[0])

        name = hxs.select(u'//div[@id="product-options-container"]/h1/text()').extract()[0].strip()
        for option in hxs.select(u'//div[@class="product-options"]/div'):
            option_name = option.select(u'.//label/text()').extract()[0].strip()

            option_identifier = option.select(u'input[@name="optionId"]/@value').extract()
            if option_identifier:
                option_identifier = identifier + '-' + option_identifier[0]
            else:
                option_identifier = identifier

            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('url', response.url)
            loader.add_value('identifier', option_identifier)
            loader.add_value('category', category)
            loader.add_value('image_url', image_url)
            loader.add_value('name', u'%s %s' % (name, option_name))

            price = option.select(u'.//div[@class="price-container sale"]/span[@class="now-price price-history-link"]/text()').extract()

            try:
                price = [re.search(u'\xa3([\d\.,]+)', price[0]).group(1)]
            except IndexError:
                price = None

            if not price:
                price = option.select(u'.//div[@class="price-container"]/span[@class="option-price"]/text()').extract()

            try:
                loader.add_value('price', price[0])
            except IndexError:
                loader.add_value('price', u'0.00')

            reviews_url = hxs.select(u'//div[@id="reviews-container"]//a[starts-with(text(), "View All")]/@href').extract()
            loader.add_value('brand', response.meta['brand'].strip().lower())
            product = loader.load_item()

            metadata = KeterMeta()
            metadata['brand'] = response.meta['brand'].strip().lower()
            metadata['reviews'] = []
            product['metadata'] = metadata

            reviews = hxs.select(u'//div[@class="review"]')
            frontpage_reviews = []
            for review in reviews:
                rating = review.select(u'.//img/@alt')[0].extract()
                rating = re.search(u'(\d) out of', rating).group(1)
                res = dict()
                res['rating'] = rating
                res['full_text'] =  review.select(u'./p[1]/text()')[0].extract().strip()

                frontpage_reviews.append(res)

            if reviews_url:
                reviews_url = urljoin_rfc(get_base_url(response), reviews_url[0])
                yield Request(reviews_url, meta={'frontpage_reviews': frontpage_reviews, 'product': product}, callback=self.parse_review, dont_filter=True)
            else:
                yield product

    def parse_review(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        reviews = hxs.select(u'//div[@class="boxproductinfo"]/table/tr')
        product = response.meta['product']

        if not reviews:
            yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%d/%m/%Y')
            loader.add_value('date', review.select(u'./td/div/p/span/text()').re(u'(\d{2}/\d{2}/\d{4})')[0])
            loader.add_xpath('full_text', u'./td/div[2]/text()')
            loader.add_value('url', response.url)

            frontpage_reviews = response.meta.get('frontpage_reviews')
            if frontpage_reviews:
                html_parser = HTMLParser()
                review_text = loader.get_output_value('full_text').strip()
                found_review = filter(lambda x: html_parser.unescape(x.get('full_text').strip()) == review_text, frontpage_reviews)
                if found_review:
                    loader.add_value('rating', found_review[0]['rating'])

            product['metadata']['reviews'].append(loader.load_item())

        next_page = hxs.select(u'//h4/a[contains(text(),"Next")]/@href').extract()

        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, meta={'product': product}, callback=self.parse_review)
        else:
            yield product
