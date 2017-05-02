__author__ = 'bayuadji'

import logging
import os
import re
import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import json

from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader
from brands import BrandSelector

HERE = os.path.abspath(os.path.dirname(__file__))


class TescoComSpider(BaseSpider):
    name = 'toymonitor-tesco.com'
    allowed_domains = ['tesco.com', 'api.bazaarvoice.com']
    start_urls = (
        'http://www.tesco.com/direct/toys/?icid=TopNav_flyoutlink_Toys',
    )
    cookie_num = 0
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}

    def parse(self, response):
        categories = response.xpath('//div[@class="menu" and h2[text()="All Toys categories"]]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url), callback=self.parse_products_list,
                          meta={'cookiejar': self.cookie_num})
            self.cookie_num += 1

        prices = response.xpath('//div[@class="product-grid shop-by" and descendant::h2[contains(text(),"Shop by price")]]//a/@href').extract()
        for url in prices:
            yield Request(response.urljoin(url), callback=self.parse_products_list,
                          meta={'cookiejar': self.cookie_num})
            self.cookie_num += 1

    def parse_product(self, response):
        url = response.url
        l = ProductLoader(item=Product(), response=response)

        name = response.xpath('//h1[@class="page-title"]/text()').extract()
        if not name:
            logging.error("ERROR! NO NAME! %s" % url)
            return
        name = name[0].strip()
        l.add_value('name', name)

        price = response.xpath('//*[@itemprop="price"]/text()').extract()
        if not price:
            logging.error("ERROR! NO PRICE! %s %s" % (url, name))
            price = ''
        l.add_value('price', price)
        identifier = response.xpath('//input[@name="skuIdVal"]/@value').extract()[0]
        if not identifier:
            logging.error("ERROR! IDENTIFIER! %s %s" % (url, name))
            return

        categories = response.xpath('//div[@id="breadcrumb"]//span[@itemprop="title"]/text()')[1:-1].extract()
        for category in categories:
            l.add_value('category', category.strip())

        l.add_value('identifier', identifier)
        l.add_value('sku', identifier)
        l.add_value('url', url)

        sku = response.xpath('//p[@itemprop="sku"]/text()').extract()
        if sku:
            l.add_value('sku', sku[0])

        image_url = response.xpath('//div[contains(@class, "static-product-image")]/img/@src').extract()
        if image_url:
            l.add_value('image_url', image_url[0])

        promo = response.xpath('//div[@id="bbSeller1"]//div[@class="savings"]//span[@class="saving"]/text()').extract()
        product = l.load_item()

        metadata = ToyMonitorMeta()
        if promo:
            metadata['promotions'] = promo[0]
        metadata['reviews'] = []
        product['metadata'] = metadata

        reviews_url = "http://api.bazaarvoice.com/data/batch.json?passkey=asiwwvlu4jk00qyffn49sr7tb&apiversion=5.5&displaycode=1235-en_gb&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A"+identifier+"&filter.q0=contentlocale%3Aeq%3Aen_AU%2Cen_CA%2Cen_DE%2Cen_GB%2Cen_IE%2Cen_NZ%2Cen_US&sort.q0=submissiontime%3Adesc&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Aen_AU%2Cen_CA%2Cen_DE%2Cen_GB%2Cen_IE%2Cen_NZ%2Cen_US&filter_reviewcomments.q0=contentlocale%3Aeq%3Aen_AU%2Cen_CA%2Cen_DE%2Cen_GB%2Cen_IE%2Cen_NZ%2Cen_US&filter_comments.q0=contentlocale%3Aeq%3Aen_AU%2Cen_CA%2Cen_DE%2Cen_GB%2Cen_IE%2Cen_NZ%2Cen_US&limit.q0=30&offset.q0=0&limit_comments.q0=3&callback=bv_1111_57408"

        request = Request(reviews_url, meta={'product': product, 'offset': 0},
                              callback=self.parse_reviews)
        yield request


    def parse_products_list(self, response):
        if 'offset' in response.url:
            j = json.loads(response.body)
            hxs = HtmlXPathSelector(text=j['products'])
            links = hxs.select('//li//h3//a[1]/@href').extract()
        else:
            links = response.xpath('//ul[@class="products"][1]/li//h3//a[1]/@href').extract()
        for link in links:  ###
            url = response.urljoin(link)
            yield Request(url, meta={'cookiejar': response.meta['cookiejar']}, callback=self.parse_product)

        if len(links) == 20:
            r = re.findall(r'offset=(\d+)', response.url)
            if r:
                off = int(r[0]) + 20
                url = re.sub(r'offset=\d+', 'offset=' + str(off), response.url)
            else:
                r = re.findall(r'catId=(\d+)', response.url)
                if r:
                    url = 'http://www.tesco.com/direct/blocks/catalog/productlisting/infiniteBrowse.jsp?&view=grid&catId=%s&sortBy=1&searchquery=&offset=20&lazyload=true' % \
                          r[0]
                    # url = urljoin(response.url, tmp[0])
            yield Request(url, method='POST', headers={'Accept': 'application/json, text/javascript, */*; q=0.01',
                                                               'AjaxRequest': 'getProducts',
                                                               'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
                                  body=url.split('.jsp?', 1)[1], meta={'cookiejar': response.meta['cookiejar']},
                                  callback=self.parse_products_list)

    def parse_reviews(self, response):
        product = response.meta['product']
        body = response.body.strip().partition('(')[-1].replace('});', '}').replace('})', '}')
        json_body = json.loads(body)

        reviews = json_body['BatchedResults']['q0']['Results']
        for review in reviews:
            review_loader = ReviewLoader(item=Review(), response=response, date_format="%d/%m/%Y")
            review_date = datetime.datetime.strptime(review['SubmissionTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
            review_loader.add_value('date', review_date.strftime('%d/%m/%Y'))

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

            next_reviews =  add_or_replace_parameter(response.url, "offset.q0", str(offset))
            request = Request(next_reviews, meta={'product': product, 'offset': offset},
                              callback=self.parse_reviews)
            yield request
        else:
            yield product
