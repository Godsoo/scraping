import os
import re
import xlrd
import json
import datetime
import paramiko
from copy import deepcopy

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from toymonitoritems import ToyMonitorMeta, Review, ReviewLoader
from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from brands import BrandSelector
HERE = os.path.abspath(os.path.dirname(__file__))

class LittleWoodsSpider(BaseSpider):
    name = 'toymonitor-littlewoods.com'
    allowed_domains = ['littlewoods.com', 'api.bazaarvoice.com']
    start_urls = ['http://www.littlewoods.com/toys/e/b/5132.end']
    errors = []
    brand_selector = BrandSelector(errors)
    #field_modifiers = {'brand': brand_selector.get_brand}

    def parse(self, response):
        categories = response.xpath('//div[@id="navigation"]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category), callback=self.parse_category)

    def parse_category(self, response):

        products = response.xpath('//a[@class="productTitle"]/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product, meta=response.meta)

        next = response.xpath('//a[@class="paginationNext"]/@href').extract()
        if next:
            next = response.urljoin(next[0])
            yield Request(next, callback=self.parse_category, meta=response.meta)

    def parse_product(self, response):
       
        loader = ProductLoader(item=Product(), response=response)
        name = ''.join(response.xpath('//h1[@class="productHeading"]//text()').extract())
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta.get('brand', ''))
        category = re.findall(u',\\ncategory: "(.*)",', response.body)
        category = category[0] if category else ''
        loader.add_value('category', category)
        loader.add_xpath('sku', '//span[@id="catalogueNumber"]/text()')
        loader.add_xpath('identifier', '//span[@id="catalogueNumber"]/text()')
        image_url = response.xpath('//div[@id="amp-originalImage"]/img/@src').extract()
        promotion = None
        if image_url:
            loader.add_value('image_url', image_url[0])
            if '3for2' in image_url[0]:
                promotion = '3 for 2'

        price = ''.join(response.xpath('//div[@class="priceNow"]//text()').extract())
        loader.add_value('price', price)

        out_of_stock = 'IN STOCK' not in ''.join(response.xpath('//meta[@property="product:availability"]/@content').extract()).upper()
        if out_of_stock:
            loader.add_value('stock', '0')

        item = loader.load_item()
        metadata = ToyMonitorMeta()
        ean = ''.join(response.xpath('//span[@id="productEAN"]/text()').extract()).strip()
        if ean:
            metadata['ean'] = ean
        metadata['reviews'] = []
        if promotion is not None:
            metadata['promotions'] = promotion
        item['metadata'] = metadata

        items = []

        amount_options = len(response.xpath('//ul[@class="customerSelection"]'))
        options = []
        # Extract option arrays
        options_text = re.findall('stockMatrix = \[(.*) \]; sdg.productOptions', ' '.join(response.body.split()))
        if options_text:
            options_text = re.findall('(.*)]; sdg.productOptions', options_text[0])
            for line in options_text[0].split(' , '):
               if '"sku' in line:
                   option = re.search('\[(.*)\]', line)
                   if option:
                       option = re.search('\[(.*)\]', line).group(0).replace('null', 'None')
                       options.append(eval(option))

        if len(options)>1:
            for option in options:
                option_item = deepcopy(item)

                name = ' '.join(option[:amount_options])
                identifier = option[amount_options]
                price = option[-5]
                
                option_item['name'] += ' ' + name
                option_item['identifier'] += '-' + identifier
                option_item['price'] = extract_price(price)
                out_of_stock = [value for value in option if value and 'out of stock' in value.lower()]
                if out_of_stock:
                    option_item['stock'] = 0
                items.append(option_item)

                
        else:        
            items.append(item)

        product_id = re.findall('productId: "(.*)"', response.body)[0]

        reviews_url = 'http://api.bazaarvoice.com/data/batch.json?passkey=2x4wql4zeys4t8mu5x3x4rb1a&apiversion=5.5&displaycode=10628-en_gb&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A'+product_id+'&filter.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&sort.q0=isfeatured%3Adesc&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&filter_reviewcomments.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&filter_comments.q0=contentlocale%3Aeq%3Aen_GB%2Cen_IE%2Cen_US&limit.q0=100&offset.q0=0&limit_comments.q0=3&callback=bv_1111_18822'

        request = Request(reviews_url, meta={'items': items, 'offset': 0, 'url': response.url},
                              callback=self.parse_reviews)
        yield request


    def parse_reviews(self, response):
        items = response.meta['items']
        url = response.meta['url']
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
            review_loader.add_value('url', url)
            
            for item in items:
                item['metadata']['reviews'].append(review_loader.load_item())

        if len(reviews) == 100:
            offset = response.meta['offset'] + 100

            next_reviews =  add_or_replace_parameter(response.url, "offset.q0", str(offset))
            request = Request(next_reviews, meta={'items': items, 'offset': offset, 'url': url},
                              callback=self.parse_reviews)
            yield request
        else:
            for item in items:
                yield item
