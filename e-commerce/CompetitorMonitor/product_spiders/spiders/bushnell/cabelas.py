import os
import csv
import re
import json
import logging
from HTMLParser import HTMLParser
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class CabelasComSpider(BaseSpider):
    name = 'bushnell-cabelas.com'
    allowed_domains = ['cabelas.com']
    start_urls = ('http://www.cabelas.com/catalog/browse/rangefinders/_/N-1102695/Ns-PRODUCT_NAME%7C0?WTz_stype=GNU&WTz_srn=SeeAllItems',
                  'http://www.cabelas.com/catalog/browse/binoculars/_/N-1102694/Ns-PRODUCT_NAME%7C0?WTz_stype=GNU&WTz_srn=SeeAllItems',
                  'http://www.cabelas.com/catalog/browse/riflescopes-red-dot/_/N-1102696/Ns-PRODUCT_NAME%7C0?WTz_srn=SeeAllItems&WTz_stype=GNU',
                  'http://www.cabelas.com/catalog/browse/binoculars/_/N-1100054/Ns-CATEGORY_SEQ_104217480?WTz_l=Unknown%3Bcat104791680%3Bcat104752080',
                  'http://www.cabelas.com/catalog/browse/riflescopes/_/N-1100055/Ns-CATEGORY_SEQ_104535180?WTz_l=Unknown%3Bcat104791680%3Bcat104752080',
                  'http://www.cabelas.com/catalog/browse/red-dots-lasers/_/N-1100061/Ns-CATEGORY_SEQ_104526180?WTz_l=Unknown%3Bcat104791680%3Bcat104752080',
                  'http://www.cabelas.com/catalog/browse/rangefinders/_/N-1100062/Ns-CATEGORY_SEQ_104525280?WTz_l=Unknown%3Bcat104791680%3Bcat104752080',
                  'http://www.cabelas.com/catalog/browse/trail-cameras-accessories/_/N-1100074/Ns-CATEGORY_SEQ_103867380?WTz_l=Unknown%3Bcat104791680%3Bcat104752080%3Bcat104243580',
                  'http://www.cabelas.com/catalog/browse/binoculars/_/N-1100245/Ns-CATEGORY_SEQ_104217480?WTz_l=SiteMap%3Bcat104752080',
                  'http://www.cabelas.com/catalog/browse/riflescopes/_/N-1100246/Ns-CATEGORY_SEQ_104535180?WTz_l=SiteMap%3Bcat104752080',
                  'http://www.cabelas.com/catalog/browse/red-dots-lasers/_/N-1100252/Ns-CATEGORY_SEQ_104526180?WTz_l=SiteMap%3Bcat104752080',
                  'http://www.cabelas.com/catalog/browse/rangefinders/_/N-1100253/Ns-CATEGORY_SEQ_104525280?WTz_l=SiteMap%3Bcat104752080',
                  'http://www.cabelas.com/catalog/browse/trail-cameras-accessories/_/N-1100265/Ns-CATEGORY_SEQ_103867380?WTz_l=SiteMap%3Bcat104752080%3Bcat104243580',
                  'http://www.cabelas.com/catalog/browse/spotting-scopes/_/N-1100060/Ns-CATEGORY_SEQ_104600880',
                  'http://www.cabelas.com/catalog/browse/spotting-scopes/_/N-1100251/Ns-CATEGORY_SEQ_104600880',
                  'http://www.cabelas.com/catalog/browse/spotting-scopes-nightvision/_/N-1102698/Ns-CATEGORY_SEQ_105679980')

    bushnell_products = {}

    def start_requests(self):
        with open(os.path.join(HERE, 'bushnell_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.bushnell_products[row['SKU'].upper().strip()] = row

        for start_url in self.start_urls:
            yield Request(start_url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        next_page = hxs.select('//div[@class="pagination"]//a[contains(text(),"Next")]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(get_base_url(response), next_page[0]))

        products = hxs.select('//a[@class="itemName"]/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        sku = hxs.select(u'//meta[@name="WT.pn_sku"]/@content').re('(\d+)')
        sku = sku[0] if sku else ''
        name = hxs.select('//div[@id="productInfo"]/div/h1[@class="label"]/text()[normalize-space()]')[0].extract().strip()
        category = hxs.select('//ul[@class="breadcrumb"]/li/a/text()').extract()
        if category:
            h = HTMLParser()
            category = h.unescape(category[-1])

        bushnell_product = self.bushnell_products.get(sku.upper().strip(), None)
        if bushnell_product:
            category = bushnell_product['Class']
            log.msg('Extracts category "%s" from bushnell file, URL: %s' % (category, response.url))

        image_url = hxs.select('//meta[@property="og:image"]/@content').extract()
        if image_url:
            image_url = image_url[0]

        products = []
        for option in hxs.select('//div[@id="productChart"]/table//tr')[2:-1]:
            loader = ProductLoader(item=Product(), response=response, selector=option)
            option_name = ' '.join([x.strip() for x in option.select('.//td/text()').extract() if x.strip()])
            identifier = option.select('.//input[@type="hidden" and @name="productId"]/@value')[0].extract().strip()
            variant_identifier = option.select('.//input[@type="hidden" and @name="productVariantId"]/@value')[0].extract().strip()
            loader.add_value('identifier', '%s.%s' % (identifier, variant_identifier))
            loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            loader.add_value('category', category)
            loader.add_value('image_url', image_url)
            loader.add_value('name', '%s %s' % (name, option_name))
            price = option.select('.//td')[-1].select('.//dl[@class="salePrice"]/dd[@class="saleprice"]/text()')
            if not price:
                price = option.select('.//td')[-1].select('.//div[@class="price"]/dl/dd[@class="nprange"]/text()')
            price = price[0].extract()
            loader.add_value('price', price)
            product = loader.load_item()
            metadata = KeterMeta()
            metadata['reviews'] = []
            metadata['brand'] = 'Bushnell'
            product['metadata'] = metadata
            products.append(product)

        if not products:
            identifier = hxs.select('.//input[@type="hidden" and @name="productId"]/@value')[0].extract().strip()
            price = hxs.select('.//dl[@class="salePrice"]/dd[@class="saleprice"]/text()')
            if not price:
                price = hxs.select('.//div[@class="price"]/dl/dd[@class="nprange"]/text()')
            if price:
                price = price[0].extract()
                loader = ProductLoader(item=Product(), response=response, selector=hxs)
                loader.add_value('identifier', identifier)
                loader.add_value('sku', sku)
                loader.add_value('url', response.url)
                loader.add_value('category', category)
                loader.add_value('image_url', image_url)
                loader.add_value('name', '%s' % name)
                loader.add_value('price', price)
                product = loader.load_item()
                metadata = KeterMeta()
                metadata['reviews'] = []
                metadata['brand'] = 'Bushnell'
                product['metadata'] = metadata
                products.append(product)
            else:
                options = re.findall('labels : \[(.*? Stock.)\]', response.body.replace('\n', ''))
                if options:
                    for i, option in enumerate(options):
                        option_value = option.replace('\'', '')
                        option_parts = option.split(' - ')
                        option_price = option_parts[-2]
                        option_name = ' - '.join(option_parts[:-2])
                        loader = ProductLoader(item=Product(), response=response, selector=hxs)
                        loader.add_value('identifier', '%s.%s' % (identifier, str(i)))
                        loader.add_value('sku', sku)
                        loader.add_value('url', response.url)
                        loader.add_value('category', category)
                        loader.add_value('image_url', image_url)
                        loader.add_value('name', '%s %s' % (name, option_name))
                        loader.add_value('price', option_price)
                        product = loader.load_item()
                        metadata = KeterMeta()
                        metadata['reviews'] = []
                        metadata['brand'] = 'Bushnell'
                        product['metadata'] = metadata
                        products.append(product)

        reviews_url = u'http://reviews.cabelas.com/8815/%s/reviews.djs?format=embeddedhtml&scrollToTop=true'
        try:
            prod_id = re.search('productId: \"(\d+)', response.body).groups()
        except AttributeError:
            return
        if not prod_id:
            prod_id = hxs.select('//input[@name="productId"]/@value').extract()
        if not prod_id:
            prod_id = re.search(r'/(\d+)\.uts', response.url).groups()
        yield Request(reviews_url % prod_id[0],
                      meta={'products': products,
                            'product_url': response.url,
                            'reviews_url': reviews_url % prod_id[0]},
                      callback=self.parse_review,
                      dont_filter=True)

    def parse_review(self, response):

        html = re.search('var materials={.*?(<div.*?)"},.initializers', response.body, re.DOTALL).group(1)
        html = re.sub(r'\\n', r'\n', html)
        html = re.sub(r'\\(.)', r'\1', html)

        hxs = HtmlXPathSelector(text=html)

        reviews = hxs.select(u'//div[starts-with(@id, "BVRRDisplayContentReviewID_")]')
        products = response.meta['products']

        if not reviews:
            for product in products:
                yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%m/%d/%Y')

            date = review.select(u'.//span[@class="BVRRValue BVRRReviewDate"]/text()').extract()[0]
            date = time.strptime(date, u'%B %d, %Y')
            date = time.strftime(u'%m/%d/%Y', date)

            loader.add_value('date', date)

            title = review.select(u'.//span[@class="BVRRValue BVRRReviewTitle"]/text()').extract()
            if not title:
                title = u'Untitled'
            else:
                title = title[0]
            text = review.select(u'.//span[@class="BVRRReviewText"]/text()').extract()
            if text:
                text = text[0]
            else:
                text = u'No text supplied.'
            loader.add_value('full_text', u'%s\n%s' % (title, text))
            loader.add_value('product_url', response.meta['product_url'])
            review_id = review.select('@id').re(r'ReviewID_(\d+)$')[0]
            loader.add_value('review_id', review_id)
            loader.add_value('url', response.meta['product_url'])
            product = products[0] if products else {}
            loader.add_value('sku', product.get('sku') or '')
            loader.add_xpath('rating', u'.//div[@id="BVRRRatingOverall_Review_Display"]//span[@class="BVRRNumber BVRRRatingNumber"]/text()')
            products[0]['metadata']['reviews'].append(loader.load_item())

        next_page = hxs.select(u'.//a[contains(text(),"Next page")]/@data-bvjsref').extract()
        if not next_page:
            for product in products:
                yield product
            return
        else:
            yield Request(urljoin_rfc(get_base_url(response), next_page[0]),
                          meta=response.meta,
                          callback=self.parse_review,
                          dont_filter=True)
