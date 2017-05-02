"""
Toy Monitor account
Very spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4754
"""

import re
import json
import datetime

from scrapy.http import Request
from scrapy.utils.url import add_or_replace_parameter

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader
from brands import BrandSelector

class Very(CrawlSpider):
    name = 'toymonitor-very.co.uk'
    allowed_domains = ['very.co.uk', 'api.bazaarvoice.com']
    start_urls = ['http://www.very.co.uk/toys/e/b/5132.end']
    
    rules = (
        Rule(LinkExtractor(restrict_css='.pagination, .facetToys, .facetOutdoorFun, .facetPartyTime'), 
             follow=True, callback='parse_products'),
        )
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}
    
    def parse_products(self, response):
        category = response.xpath('//div[@id="breadcrumb"]//span[@itemprop="name"]/text()').extract()[2:]
        for product in response.css('.productList .product'):
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('identifier', '@id', re='product-(.+)')
            loader.add_xpath('url', './/@href')
            brand = product.xpath('.//h3/em/text()').extract_first()
            name = product.xpath('.//h3/span/text()').extract_first()
            if name[0].islower():
                loader.add_value('name', brand)
            loader.add_value('name', name)
            loader.add_css('price', '.productPrice dd:last-child::text')
            loader.add_xpath('sku', '@id', re='product-(.+)')
            loader.add_value('category', category)
            loader.add_css('image_url', '.productMainImage img::attr(src)')
            image_url = loader.get_output_value('image_url')
            promotion = None
            if image_url and '3for2' in image_url:
                promotion = '3 for 2'
            loader.add_value('brand', brand)
            loader.add_value('shipping_cost', '3.99')
            stock = product.css('.productStock dd').extract_first().title()
            if 'In Stock' not in stock and 'Low Stock' not in stock:
                loader.add_value('stock', 0)
            product = loader.load_item()
        
            metadata = ToyMonitorMeta()
            metadata['reviews'] = []
            if promotion:
                metadata['promotions'] = promotion
            product['metadata'] = metadata

            prod_id = re.findall("/(\d+).prd", product['url'])[0]
            reviews_url = "http://api.bazaarvoice.com/data/batch.json?passkey=35w0b6mavcfmefkhv3fccjwcc&apiversion=5.5&displaycode=17045-en_gb&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A"+prod_id+"&filter.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&sort.q0=isfeatured%3Adesc&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&filter_reviewcomments.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&filter_comments.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&limit.q0=100&offset.q0=0&limit_comments.q0=3&callback=bv_1111_57043"

            request = Request(reviews_url, meta={'product': product, 'offset': 0},
                              callback=self.parse_reviews)
            yield request

    def parse_reviews(self, response):
        product = response.meta['product']
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

            next_reviews =  add_or_replace_parameter(response.url, "offset.q0", str(offset))
            request = Request(next_reviews, meta={'product': product, 'offset': offset},
                              callback=self.parse_reviews)
            yield request
        else:
            yield product
