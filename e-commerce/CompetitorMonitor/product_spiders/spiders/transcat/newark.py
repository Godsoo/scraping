# -*- coding: utf-8 -*-
"""
Account: Transcat
Name: transcat-newark.com
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4825
Use the MPN’s that are found in the metadata of the client spider and search on site.

Original developer: Franco Almonacid <fmacr85@gmail.com>
"""


import re
import os
import csv
import json
import datetime

from scrapy.utils.url import add_or_replace_parameter, url_query_parameter

from scrapy import Spider, FormRequest, Request
from product_spiders.items import (
    ProductLoaderWithNameStrip as ProductLoader,
    Product,
)

from product_spiders.utils import extract_price
from transcatitems import TranscatMeta, Review, ReviewLoader
from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class NewarkSpider(Spider):
    name = 'transcat-newark.com'
    allowed_domains = ['newark.com', 'api.bazaarvoice.com']

    filename = os.path.join(HERE, 'Transcatfeed.csv')
    start_urls = ('file://' + filename,)


    def parse(self, response):
        search_url = 'http://www.newark.com/webapp/wcs/stores/servlet/Search?catalogId=15003&langId=-1&storeId=10194&categoryName=All%20Categories&selectedCategoryId=&gs=true&st='
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            mpn = '"'+row['MPN']+'"'
            yield Request(search_url+mpn, callback=self.parse_search, meta={'row': row})

    def parse_search(self, response):

        result_categories = response.xpath('//ul[@class="categoryList"]//a/@href').extract()
        if result_categories:
            for result_category in result_categories:
                url = response.urljoin(result_category)
                url = add_or_replace_parameter(url, 'showResults', 'true')
                url = add_or_replace_parameter(url, 'aa', 'true')
                yield Request(url, callback=self.parse_search, meta=response.meta)

        products = response.xpath('//tr/td[@class="mftrPart"]/p/a/@href').extract()
        if products:
            for product in products:
                yield Request(response.urljoin(product), callback=self.parse_product, meta=response.meta)

            next = response.xpath('//a[@class="nextLinkPara"]/@href').extract()
            if next:
                next_page = int(url_query_parameter(response.url, 'beginIndex', '1'))
                next_url = add_or_replace_parameter(response.url, 'beginIndex', str(next_page + 1 ))
                yield Request(next_url, callback=self.parse_search, meta=response.meta)

        identifier = response.xpath('//input[@id="itemsArray"]/@value').extract()
        if identifier:
            for item in self.parse_product(response):
                yield item

    def parse_product(self, response):
        name = ' '.join(response.xpath('//h1/text()').extract()[0].split())
        identifier = response.xpath('//input[@id="itemsArray"]/@value').extract()[0]
        sku = response.xpath('//span[@itemprop="mpn"]/text()').extract()
        sku = sku[0].strip() if sku else ''

        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        price = extract_price(price[0]) if price else '0'

        brand = response.xpath('//dd[contains(@itemtype, "Organization")]//a/text()').extract()
        brand = brand[0].strip() if brand else ''

        categories = response.xpath('//div[@id="breadcrumb"]//a/text()').extract()[1:-1]

        product_image = response.xpath('//img[@id="productMainImage"]/@src').extract()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('price', price)

        if product_image:
            loader.add_value('image_url', response.urljoin(product_image[0]))

        loader.add_value('brand', brand)
        loader.add_value('category', categories)

        stock = response.xpath('//span[contains(@class, "availability")]//text()').re('\d+')
        if not stock:
            loader.add_value('stock', 0)
        else:
            stock = extract_price(stock[0])
            loader.add_value('stock', stock)

        product = loader.load_item()
        metadata = TranscatMeta()
        metadata['reviews'] = []
        product['metadata'] = metadata

        reviews_url = "http://api.bazaarvoice.com/data/batch.json?passkey=tkfeqezs3t1ybjthb77uxbvqd&apiversion=5.5&displaycode=1015-en_us&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A"+identifier+"&filter.q0=contentlocale%3Aeq%3Aen_CA%2Cen_US&sort.q0=submissiontime%3Adesc&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Aen_CA%2Cen_US&filter_reviewcomments.q0=contentlocale%3Aeq%3Aen_CA%2Cen_US&filter_comments.q0=contentlocale%3Aeq%3Aen_CA%2Cen_US&limit.q0=100&offset.q0=0&limit_comments.q0=3&callback=bv_1111_4827"

        request = Request(reviews_url, meta={'product': product, 'offset': 0, 'identifier': identifier},
                              callback=self.parse_reviews)
        yield request


    def parse_reviews(self, response):
        product = response.meta['product']
        identifier = response.meta['identifier']
        body = response.body.strip().partition('(')[-1].replace('});', '}').replace('})', '}')
        json_body = json.loads(body)

        reviews = json_body['BatchedResults']['q0']['Results']
        for review in reviews:
            review_loader = ReviewLoader(item=Review(), response=response, date_format="%B %d, %Y")
            review_date = datetime.datetime.strptime(review['SubmissionTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
            review_loader.add_value('date', review_date.strftime("%B %d, %Y"))

            title = review['Title']
            text = review['ReviewText']

            if title:
                full_text = title + '\n' + text
            else:
                full_text = text

            pros = review['Pros']
            cons = review['Cons']
            if pros:
                full_text += '\nPros: ' + ', '.join(pros)
            if cons:
                full_text += '\nCons: ' + ', '.join(cons)


            review_loader.add_value('full_text', full_text)
            rating = review['Rating']
            review_loader.add_value('rating', rating)
            review_loader.add_value('url', product['url'])

            product['metadata']['reviews'].append(review_loader.load_item())

        if len(reviews) == 100:
            offset = response.meta['offset'] + 100

            next_reviews = "http://api.bazaarvoice.com/data/batch.json?passkey=tkfeqezs3t1ybjthb77uxbvqd&apiversion=5.5&displaycode=1015-en_us&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A"+identifier+"&filter.q0=contentlocale%3Aeq%3Aen_CA%2Cen_US&sort.q0=submissiontime%3Adesc&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Aen_CA%2Cen_US&filter_reviewcomments.q0=contentlocale%3Aeq%3Aen_CA%2Cen_US&filter_comments.q0=contentlocale%3Aeq%3Aen_CA%2Cen_US&limit.q0=100&offset.q0="+str(offset)+"&limit_comments.q0=3&callback=bv_1111_4827"
            request = Request(next_reviews, meta={'product': product, 'offset': offset, 'identifier': identifier},
                              callback=self.parse_reviews)
            yield request
        else:
            yield product

