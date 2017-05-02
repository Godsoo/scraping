# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import json

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from product_spiders.utils import extract_price

from product_spiders.base_spiders.target.targetspider import BaseTargetSpider


class TargetTestSpider(BaseTargetSpider):
    name = 'mattelmegabloks-target.com-test'
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

    def parse(self, response):
        for key, brand in self.keys:
            self.log('Searching ' + key)
            yield FormRequest.from_response(response, formname='CatalogSearchForm', formdata={'searchTerm':key}, meta={'brand':brand}, callback=self.parse_list)

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

    def parse_product(self, response):
        try:
            request = super(TargetTestSpider, self).parse_product(response).next()
        except StopIteration:
            return
        product = request.meta.get('product')
        if product:
            identifier = product['identifier']
            if identifier in self.found_ids:
                return
            self.found_ids.add(identifier)

            self.log("[[TESTING]] Product sku: '%s'" % product['sku'])
            if product['sku'] == '' or product['sku'] is None or not product['sku']:
                product['sku'] = product['identifier']

            product['metadata']['brand'] = product['brand'].strip().lower()

            hxs = HtmlXPathSelector(response)
            tmp = hxs.select('//div[@id="price_main"]//span[@itemprop="price"]/text()').extract()
            if tmp:
                price = extract_price(tmp[0])
                product['price'] = price
                product['stock'] = 1
            else:
                product['price'] = '0.0'
                product['stock'] = 0

            request.meta['product'] = product
        yield request

    def parse_review(self, product_url, review, review_loader):
        parsed_review = super(TargetTestSpider, self).parse_review(product_url, review, review_loader)
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
        parsed_review['full_text'] = full_text
        return parsed_review

    # def _get_reviews_url(self, identifier, offset=0):
    #     url = "http://api.bazaarvoice.com/data/batch.json?passkey=aqxzr0zot28ympbkxbxqacldq&apiversion=5.5&" \
    #           "displaycode=19988-en_us&resource.q0=products&filter.q0=id%3Aeq%3A{identifier}&stats.q0=reviews&" \
    #           "filteredstats.q0=reviews&filter_reviews.q0=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&" \
    #           "filter_reviewcomments.q0=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&resource.q1=reviews&" \
    #           "filter.q1=isratingsonly%3Aeq%3Afalse&filter.q1=productid%3Aeq%3A{identifier}&" \
    #           "filter.q1=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&sort.q1=submissiontime%3Adesc&" \
    #           "stats.q1=reviews&filteredstats.q1=reviews&include.q1=authors%2Cproducts%2Ccomments&" \
    #           "filter_reviews.q1=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&" \
    #           "filter_reviewcomments.q1=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&" \
    #           "filter_comments.q1=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&limit.q1=8&offset.q1={offset}&" \
    #           "limit_comments.q1=3&resource.q2=reviews&filter.q2=productid%3Aeq%3A{identifier}&" \
    #           "filter.q2=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&limit.q2=1&resource.q3=reviews&" \
    #           "filter.q3=productid%3Aeq%3A{identifier}&filter.q3=isratingsonly%3Aeq%3Afalse&" \
    #           "filter.q3=rating%3Agt%3A3&filter.q3=totalpositivefeedbackcount%3Agte%3A3&" \
    #           "filter.q3=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&sort.q3=totalpositivefeedbackcount%3Adesc&" \
    #           "stats.q3=reviews&filteredstats.q3=reviews&include.q3=authors%2Creviews&" \
    #           "filter_reviews.q3=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&" \
    #           "filter_reviewcomments.q3=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&limit.q3=1&" \
    #           "resource.q4=reviews&filter.q4=productid%3Aeq%3A{identifier}&filter.q4=isratingsonly%3Aeq%3Afalse&" \
    #           "filter.q4=rating%3Alte%3A3&filter.q4=totalpositivefeedbackcount%3Agte%3A3&" \
    #           "filter.q4=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&sort.q4=totalpositivefeedbackcount%3Adesc&" \
    #           "stats.q4=reviews&filteredstats.q4=reviews&include.q4=authors%2Creviews&" \
    #           "filter_reviews.q4=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&" \
    #           "filter_reviewcomments.q4=contentlocale%3Aeq%3Aen_CA%2Cen_GB%2Cen_US%2Cen&limit.q4=1&" \
    #           "callback=BV._internal.dataHandler0".format(identifier=identifier, offset=str(offset))
    #     return url
