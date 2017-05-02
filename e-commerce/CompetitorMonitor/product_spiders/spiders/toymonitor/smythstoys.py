import os
import xlrd
import json
import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from urlparse import urljoin

from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
from brands import BrandSelector

HERE = os.path.abspath(os.path.dirname(__file__))


class SmythsToysSpider(BaseSpider):
    name = 'toymonitor-smythstoys.com'
    allowed_domains = ['smythstoys.com', 'api.bazaarvoice.com']
    start_urls = ['http://www.smythstoys.com/uk/en-gb/c-320/toys/',]
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}
    
    def parse(self, response):
        categories = response.xpath('//li[contains(@class,"menu-item") and span[text()="Toys"]]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category), callback=self.parse_categories)

    def parse_categories(self, response):
        site_brands = response.xpath('//ul[contains(@class, "attr_Brand")]/li/a')
        for brand in site_brands:
            brand_name = brand.xpath('./span[1]/text()').extract()[0].split("(")[0].strip()
            brand_url = brand.xpath('@href').extract()[0]
            yield Request(response.urljoin(brand_url), callback=self.parse_brand, meta={'brand': brand_name})

        site_ages = response.xpath('//ul[contains(@class, "attr_AgeRange")]/li/a/@href').extract()
        for age in site_ages:
            yield Request(response.urljoin(age), callback=self.parse_brand)

        for item in self.parse_brand(response):
            yield item

    def parse_brand(self, response):
        products = response.xpath('//div[contains(@class, "listing-item") and contains(@class, "product")]')

        pages = response.xpath('//ul[contains(@class, "pagination") and contains(@class, "pages") and contains(@class, "pagination-sm")]'
            '//a[contains(@class, "ajax-link") and not(contains(@class, "selected"))]/@href').extract()
        if products:
            for page in pages:
                yield Request(response.urljoin(page), callback=self.parse_brand, meta=response.meta)
        category_name = response.xpath('//h1[contains(@class, "category-name")]/text()').re(r'^(.*) \(\d+\)')

        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            try:
                product_name = product.xpath('.//div[@class="product-description"]/a[contains(@class, "product-name")]/text()').extract()[0].strip()
            except:
                continue
            else:
                loader.add_value('name', product_name)
                loader.add_value('brand', response.meta.get('brand', ''))
                loader.add_xpath('url', './/div[@class="product-description"]/a[contains(@class, "product-name")]/@href', lambda u: response.urljoin(u[0]))
                loader.add_xpath('identifier', './/div[@class="product-description"]/a[contains(@class, "product-name")]/@href', re=r'/p-(\d+)/')
                loader.add_xpath('image_url', './/div[@class="image"]//img/@src')
                sku = product.xpath('./div/a/@data-event').re('"id": "([0-9]+)"')
                if sku:
                    loader.add_value('sku', sku[0])
                price = product.xpath('.//div[@class="pricing-container"]//span[@class="price now"]')
                if not price:
                    price = product.xpath('.//div[@class="pricing-container"]')
                price = price.re(r'([\d,.]+)')[-1]
                loader.add_value('price', price)
                sku = product_name.split(' ')[-1]
                if not sku:
                    self.log('ERROR: no SKU found! URL:{}'.format(response.url))
                else:
                    loader.add_value('sku', sku)
                loader.add_value('category', category_name)

                item = loader.load_item()

                metadata = ToyMonitorMeta()
                metadata['reviews'] = []
                item['metadata'] = metadata

                product_id = product.xpath('.//a[@class="ega-prodclick"]/@data-event').re('"id": "(.*)"')[0]

                reviews_url = 'http://api.bazaarvoice.com/data/batch.json?passkey=lquk3xwywjr5jl6ty8h5wc2kx&apiversion=5.5&displaycode=17935-en_gb&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A'+product_id+'&filter.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&sort.q0=submissiontime%3Adesc&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&filter_reviewcomments.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&filter_comments.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&limit.q0=100&offset.q0=0&limit_comments.q0=3&callback=bv_1111_55059'

                request = Request(reviews_url, meta={'item': item, 'offset': 0},
                                      callback=self.parse_reviews)
                yield request


    def parse_reviews(self, response):
        item = response.meta['item']
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
            review_loader.add_value('url', item['url'])

            item['metadata']['reviews'].append(review_loader.load_item())

        if len(reviews) == 100:
            offset = response.meta['offset'] + 100

            next_reviews =  add_or_replace_parameter(response.url, "offset.q0", str(offset))
            request = Request(next_reviews, meta={'item': item, 'offset': offset},
                              callback=self.parse_reviews)
            yield request
        else:
            yield item
