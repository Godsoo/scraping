__author__ = 'bayuadji'

import json
import datetime

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader

import logging


class TescoComKeterSpider(BaseSpider):
    name = 'tesco.com_keter'
    allowed_domains = ['tesco.com', 'api.bazaarvoice.com']
    start_urls = (
        'http://www.tesco.com/direct/',
        )

    search_url = 'http://www.tesco.com/direct/search-results/results.page?catId=4294967294&searchquery='

    products = ['Keter',
                'Suncast',
                'Rubbermaid',
                'Lifetime',
                'Step 2',
                'Sterilite']
    cats = ['kitchen',
            'garden',
            'furniture',
            'diy']

    individual_products = [
        ('Keter', 'http://www.tesco.com/direct/keter-belle-vue-plastic-shed/213-4349.prd?pageLevel=&skuId=213-4349'),
    ]

    def start_requests(self):
        for keyword in self.products:
            url = self.search_url + keyword
            request = Request(url, callback=self.parse_search)
            request.meta['brand'] = keyword
            yield request

        for brand, url in self.individual_products:
            request = Request(url, callback=self.parse_product)
            request.meta['brand'] = brand
            yield request

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url
        brand = response.meta.get('brand', '')

        name = hxs.select("//div[@class='primary-content']//div[@id='product-title']/h1/text()").extract()
        if not name:
            logging.error("ERROR! NO NAME! %s" % url)
            return
        name = name[0]

        price = hxs.select("//div[@class='secondary-content']//ul[@class='pricing']/li[@class='current-price']/span/text()").extract()
        if not price:
            logging.error("ERROR! NO PRICE! %s %s" % (url, name))
            price = ''
        else:
            price = "".join(price[:2])
        sku = url.lower().split('skuid=')[-1] if len(url.lower().split('skuid=')) > 0 else None
        if not sku:
            logging.error("ERROR! SKU! %s %s" % (url, name))
            return
        categories = " ".join(hxs.select("//div[@id='breadcrumbs']//li//a/text()").extract()).lower().replace('\n', ' ').split(' ')

        if 'books' in categories:
            logging.error("ERROR! Product not valid  %s %s" % (url, name))
            return

        #is_valid = [t for t in self.cats if t in categories]
        #if brand.lower() != 'keter' and not is_valid:
        #    logging.error("ERROR! Product not valid  %s %s" % (url, name))
        #    return

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', sku)
        l.add_value('name', name)
        l.add_value('url', url)
        l.add_value('price', price)
        l.add_value('brand', brand.strip().lower())
        #l.add_value('sku', sku)
        product = l.load_item()
        metadata = KeterMeta()
        metadata['brand'] = brand.strip().lower()
        metadata['reviews'] = []
        product['metadata'] = metadata

        review_url = 'http://api.bazaarvoice.com/data/batch.json?passkey=asiwwvlu4jk00qyffn49sr7tb&apiversion=5.4&displaycode=1235-en_gb&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A'+sku+'&filter.q0=contentlocale%3Aeq%3Aen_AU%2Cen_CA%2Cen_DE%2Cen_GB%2Cen_IE%2Cen_NZ%2Cen_US&sort.q0=rating%3Adesc&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Aen_AU%2Cen_CA%2Cen_DE%2Cen_GB%2Cen_IE%2Cen_NZ%2Cen_US&limit.q0=100&offset.q0=0&limit_comments.q0=3&callback=bv182_28795'
        request = Request(review_url, meta={'product': product, 'offset':0, 'sku':sku},
                              callback=self.parse_reviews)
        yield request

    def parse_reviews(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']
        sku = response.meta['sku']
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
                full_text = title[0] + '\n' + text
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
            next_reviews = 'http://api.bazaarvoice.com/data/batch.json?passkey=asiwwvlu4jk00qyffn49sr7tb&apiversion=5.4&displaycode=1235-en_gb&resource.q0=reviews&filter.q0=isratingsonly%3Aeq%3Afalse&filter.q0=productid%3Aeq%3A'+sku+'&filter.q0=contentlocale%3Aeq%3Aen_AU%2Cen_CA%2Cen_DE%2Cen_GB%2Cen_IE%2Cen_NZ%2Cen_US&sort.q0=rating%3Adesc&stats.q0=reviews&filteredstats.q0=reviews&include.q0=authors%2Cproducts%2Ccomments&filter_reviews.q0=contentlocale%3Aeq%3Aen_AU%2Cen_CA%2Cen_DE%2Cen_GB%2Cen_IE%2Cen_NZ%2Cen_US&limit.q0=100&offset.q0='+str(offset)+'&limit_comments.q0=3&callback=bv182_28795'
            request = Request(next_reviews, meta={'product': product, 'offset':offset, 'sku':sku},
                              callback=self.parse_reviews)
            yield request
        else:
            if product['price']:
                yield product

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        brand = response.meta.get('brand', '')
        # parse pages
        pages = hxs.select("//div[@class='pagination-link']//a/@href").extract()
        for page in pages:
            request = Request(urljoin_rfc(base_url, page), callback=self.parse_search)
            request.meta['brand'] = brand
            yield request

        # parse products
        items = hxs.select("//li[contains(@class, 'product')]")
        for item in items:
            name = item.select("div[@class='product-details']/div[contains(@class, 'product-name')]/h3/a/text()").extract()
            if not name:
                continue

            url = item.select("div[@class='product-details']/div[contains(@class, 'product-name')]/h3/a/@href").extract()
            if not url:
                logging.error("ERROR! NO URL! URL: %s. NAME: %s" % (response.url, name))
                continue
            url = url[0]
            url = urljoin_rfc(base_url, url)

            request = Request(url, callback=self.parse_product)
            request.meta['brand'] = brand
            yield request
