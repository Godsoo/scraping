# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import json

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from product_spiders.utils import extract_price

from product_spiders.base_spiders.target.targetspider import BaseTargetSpider


class TargetSpider(BaseTargetSpider):
    name = 'mattelmegabloks-target.com'
    start_urls = ('http://www.target.com',)
    category_type = 'single'

    found_ids = set()
    keys = [
        ('Mattel', 'Mattel'),
        ('Barbie', 'Mattel'),
        ('Hot Wheels', 'Mattel'),
        ('Monster High', 'Mattel'),
        ('WWE', 'Mattel'),
        ('Disney princess', 'Mattel'),
        ('Max Steel', 'Mattel'),
        ('Ever After High', 'Mattel'),
        ('Matchbox', 'Mattel'),
        ('Little Mommy', 'Mattel'),
        ('Cars', 'Mattel'),
        ('Polly Pocket', 'Mattel'),
        ('DC Universe', 'Mattel'),
        ('Sofia the First', 'Mattel'),
        ('Planes', 'Mattel'),
        ('Frozen', 'Mattel'),
        ('Toy Story', 'Mattel'),
        ('Fijit Friends', 'Mattel'),
        ('Mega Bloks', 'Mega Bloks'),
        ("Assassin's Creed", 'Mega Bloks'),
        ('Call of Duty', 'Mega Bloks'),
        ('Cat', 'Mega Bloks'),
        (u'Create ‘n Play', 'Mega Bloks'),
        ("Create 'n Play Junior", 'Mega Bloks'),
        ('Dora the Explorer', 'Mega Bloks'),
        ('First Builders', 'Mega Bloks'),
        ('Halo', 'Mega Bloks'),
        ('Hello Kitty', 'Mega Bloks'),
        ('Jeep', 'Mega Bloks'),
        ('John Deere', 'Mega Bloks'),
        ('Junior Builders', 'Mega Bloks'),
        ('Kapow', 'Mega Bloks'),
        ('Mega Play', 'Mega Bloks'),
        ('power rangers', 'Mega Bloks'),
        ('Ride-ons', 'Mega Bloks'),
        ('Ride ons', 'Mega Bloks'),
        ('Skylanders', 'Mega Bloks'),
        ('spongebob squarepants', 'Mega Bloks'),
        ('thomas and friends', 'Mega Bloks'),
        ('world builders', 'Mega Bloks'),
    ]

    def start_requests(self):
        for key, brand in self.keys:
            self.log('Searching ' + key)
            url = 'http://tws.target.com/searchservice/item/search_results/v2/by_keyword?search_term=%s&alt=json&pageCount=900000&response_group=Items&zone=mobile&offset=0' %key
            yield Request(url, meta={'brand':brand})

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        # Crawl products.
        urls = hxs.select('//ul[contains(@class,"productsListView")]/li/ul/li//a[contains(@class,"productClick")][1]/@href').extract()
        self.log("[[TESTING]] URLs found: %d" % len(urls))
        for url in hxs.select('//ul[contains(@class,"productsListView")]/li/ul/li//a[contains(@class,"productClick")][1]/@href').extract():
            yield Request(url, meta={'brand':response.meta['brand']}, callback=self.parse_product)

        tmp = hxs.select('//ul[@class="lpPagination"]/li[@class="pagination--next"]/a/@href').extract()
        if tmp:
            formData = [response.url.split('searchTerm=')[1].split('&')[0], 60]
            stateData = ''
            tmp = hxs.select('//form[@id="dimensions"]//ul[@class="menu"]/li[contains(@class,"expanded")]/@id').extract()
            if tmp:
                stateData = ','.join(['"%s":"show"' % s for s in tmp])

            yield FormRequest('http://www.target.com/SoftRefreshProductListView', formdata={'formData':'#navigation=true&searchTerm=%s&sortBy=relevance&Nao=%d&viewType=medium&category=0|All|matchallpartial|all+categories' % tuple(formData), 'stateData':stateData, 'isDLP':'false', 'response_group':'Items'}, meta={'brand':response.meta['brand'], 'formData':formData, 'stateData':stateData}, callback=self.parse_list_next)

    def parse_list_next(self, response):
        jdata = json.loads(response.body)
        hxs = HtmlXPathSelector(text=jdata['productListArea']['productListForm'])
        urls = hxs.select('//a[contains(@class,"productClick productTitle")]/@href').extract()
        self.log("[[TESTING]] 2 URLs found: %d" % len(urls))
        for url in urls:
            yield Request(url, meta={'brand':response.meta['brand']}, callback=self.parse_product)
        # Crawl next page
        if len(urls) == 60:
            formData = response.meta['formData']
            formData[1] += 60
            stateData = response.meta['stateData']
            yield FormRequest('http://www.target.com/SoftRefreshProductListView', formdata={'formData':'#navigation=true&searchTerm=%s&sortBy=relevance&Nao=%d&viewType=medium&category=0|All|matchallpartial|all+categories' % tuple(formData), 'stateData':stateData, 'isDLP':'false', 'response_group':'Items'}, meta={'brand':response.meta['brand'], 'formData':formData, 'stateData':stateData}, callback=self.parse_list_next)

    def parse_product_json(self, response):
        try:
            request = super(TargetSpider, self).parse_product_json(response).next()
        except StopIteration:
            return
        product = request.meta.get('product')
        if product:
            identifier = product['identifier']
            if identifier in self.found_ids:
                return
            self.found_ids.add(identifier)

            if not product.get('sku'):
                product['sku'] = product['identifier']
            self.log("[[TESTING]] Product sku: '%s'" % product['sku'])
            
            product['metadata']['brand'] = product['brand'].strip().lower()
            request.meta['product'] = product
        yield request

    def get_review_full_text(self, review):
        title = review['Title']
        text = review['ReviewText']
        if title:
            full_text = title + '\n' + text
        else:
            full_text = text
        extra_text = ''
        pros = review['Pros']
        cons = review['Cons']
        if pros:
            extra_text += '\nPros: ' + ', '.join(pros)
        if cons:
            extra_text += '\nCons: ' + ', '.join(cons)
        if 'Entertaining' in review['SecondaryRatings']:
            extra_text += '\nEntertaining: %s' % review['SecondaryRatings']['Entertaining']['Value']
        if 'Quality' in review['SecondaryRatings']:
            extra_text += '\nQuality: %s' % review['SecondaryRatings']['Quality']['Value']
        if 'Value' in review['SecondaryRatings']:
            extra_text += '\nValue: %s' % review['SecondaryRatings']['Value']['Value']
        if review['IsRecommended']:
            extra_text += '\nYes, I recommend this product.'
        if extra_text:
            full_text += ' #&#&#&# ' + extra_text
        return full_text
