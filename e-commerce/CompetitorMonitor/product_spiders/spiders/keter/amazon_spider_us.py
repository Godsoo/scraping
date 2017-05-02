import csv
import os
import re
import time
import json
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.BeautifulSoup import BeautifulSoup
from keteritems import KeterMeta, Review, ReviewLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonSpider(BaseSpider):
    name = 'keter-amazon.com'
    allowed_domains = ['amazon.com']
    user_agent = 'spd'

    ids = []

    def start_requests(self):
        brands = ['step2', 'rubbermaid', 'lifetime', 'keter', 'suncast', 'sterilite']
        with open(os.path.join(HERE, 'amazonus_urls.csv')) as f:
            reader = csv.reader(f)
            search_urls = [row[0] for row in reader]
        for url in search_urls:
            for brand in brands:
                yield Request(url % brand, meta={'brand': brand})
        extra_products = {'rubbermaid': [u'http://www.amazon.com/s/ref=bl_sr_appliances?_encoding=UTF8&field-brandtextbin=Rubbermaid%20Commercial%20Products&node=2619525011',
                                         u'http://www.amazon.com/s/ref=bl_sr_industrial?field-brandtextbin=Rubbermaid+Commercial+Products&node=16310091',
                                         u'http://www.amazon.com/s/ref=bl_sr_hi?_encoding=UTF8&field-brandtextbin=Rubbermaid%20Commercial%20Products&node=228013',
                                         u'http://www.amazon.com/s/ref=bl_sr_baby-products?_encoding=UTF8&field-brandtextbin=Rubbermaid%20Commercial%20Products&node=165796011',
                                         u'http://www.amazon.com/Rubbermaid/pages/2599887011/ref=ams_dp_byline_2599887011',
                                         u'http://www.amazon.com/s/ref=bl_sr_appliances?_encoding=UTF8&field-brandtextbin=Rubbermaid&node=2619525011',
                                         u'http://www.amazon.com/s/ref=bl_sr_lawn-garden?_encoding=UTF8&field-brandtextbin=Rubbermaid&node=2972638011',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_0?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Agarden&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_1?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Aindustrial&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_2?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Ahpc&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_3?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Aoffice-products&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_4?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Atools&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_5?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Alawngarden&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_7?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Asporting&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_8?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Aautomotive&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_9?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Aelectronics&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_10?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Ababy-products&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_11?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Atoys-and-games&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_13?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Apets&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_14?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Aapparel&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=lp_2599887011_nr_i_16?srs=2599887011&rh=i%3Aspecialty-aps%2Ci%3Ashoes&ie=UTF8&qid=1373976991',
                                         u'http://www.amazon.com/s/ref=bl_sr_industrial?field-brandtextbin=Rubbermaid+Commercial&node=16310091'],
                          'sterilite': [u'http://www.amazon.com/s/ref=bl_sr_kitchen?_encoding=UTF8&field-brandtextbin=Sterilite%20Corp.&node=1055398',
                                         u'http://www.amazon.com/s/ref=bl_sr_beauty?_encoding=UTF8&field-brandtextbin=STERILITE&node=3760911',
                                         u'http://www.amazon.com/s/ref=bl_sr_home-garden?_encoding=UTF8&field-brandtextbin=STERILITE&node=1055398'],
                           'keter': [u'http://www.amazon.com/s/ref=bl_sr_lawn-garden/176-4543789-7819600?_encoding=UTF8&field-brandtextbin=Keter%20North%20America%20LLC&node=2972638011',
                                     u'http://www.amazon.com/s/ref=bl_sr_home-garden?_encoding=UTF8&field-brandtextbin=Keter%20Rattan&node=1055398'],
                           'lifetime': [u'http://www.amazon.com/s/ref=bl_sr_lawn-garden?_encoding=UTF8&field-brandtextbin=Lifetime%20Products&node=2972638011',
                                        u'http://www.amazon.com/s/ref=bl_sr_appliances?_encoding=UTF8&field-brandtextbin=Lifetime%20Brands&node=2619525011',
                                        u'http://www.amazon.com/s/ref=bl_sr_home-garden?_encoding=UTF8&field-brandtextbin=Lifetime%20Brands%20Inc&node=1055398',
                                        u'http://www.amazon.com/s/ref=bl_sr_home-garden?_encoding=UTF8&field-brandtextbin=Lifetime&node=1055398',
                                        u'http://www.amazon.com/s/ref=bl_sr_home-garden?_encoding=UTF8&field-brandtextbin=Lifetime%20Brands&node=1055398'],
                          'suncast': [u'http://www.amazon.com/s/ref=bl_sr_home-garden?_encoding=UTF8&field-brandtextbin=Suncast&node=1055398'],
                          'step2': [u'http://www.amazon.com/s/ref=bl_sr_home-garden?_encoding=UTF8&field-brandtextbin=Step2&node=1055398']}

        for brand, url_list in extra_products.items():
            for url in url_list:
                yield Request(url, meta={'brand': brand})

    def parse(self, response):
        soup = BeautifulSoup(response.body)
        next_page = soup.find('a', 'pagnNext')
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page['href'])
            yield Request(next_page, meta=response.meta)

        hxs = HtmlXPathSelector(response)

        next_page = hxs.select('//a[@id="pagnNextLink"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(get_base_url(response), next_page[0]), meta=response.meta)

        products = soup.findAll('div', id=re.compile(u'^result_.*'))
        for product in products:
            # parent_expressions = (lambda tag: tag.name == 'h3' and tag.get('class') == 'title',
            #                      lambda tag: tag.name == 'div' and tag.get('class') == 'productTitle')
            url = product.find('h3', 'newaps').find('a') if product.find('h3', 'newaps') else ''
            if url:
                url = urljoin_rfc(get_base_url(response), url['href'])
                yield Request(url, meta=response.meta, callback=self.parse_options)

        for result in hxs.select(u'//div[@id="atfResults" or @id="btfResults"]//div[starts-with(@id, "result_")]'):
            try:
                url = result.select(u'.//h3/a/@href').extract()[0]
            except:
                continue
            yield Request(url, meta=response.meta, callback=self.parse_options)

    def parse_options(self, response):
        try:
            options = json.loads(re.findall(r'var asin_variation_values = ({.*});  var stateData', response.body.replace('\n', ''))[0])
        except:
            pass
        else:
            self.log('>>>> OPTIONS FOUND => %s' % response.url)
            identifier = re.findall(r'/dp/(\w+)/', response.url)[0]
            for id in options.keys():
                option_url = response.url.replace(identifier, id)
                self.log('>>>> PROCESS OPTION ID %s => %s' % (id, option_url))
                yield Request(option_url,
                              meta=response.meta,
                              callback=self.parse_product)
        # Current item
        for item in self.parse_product(response):
            yield item


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        option_label = ' '.join(hxs.select('//div[@class="variationSelected"]'
                                           '/*[@class="variationLabel"]/text()').extract())

        loader = ProductLoader(item=Product(), selector=hxs)
        soup = BeautifulSoup(response.body)
        try:
            name = ' '.join([soup.find('span', id='btAsinTitle').text, option_label]).strip()
        except:
            name = ' '.join([hxs.select('//h1[@id="title"]/text()').extract()[0].strip(), option_label]).strip()
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        no_price_ = False
        try:
            soup_form = soup.find(id='handleBuy')
            price = soup_form.find('b', 'priceLarge')
            if not price:
                price = soup_form.find('span', 'price')
            if not price:
                price = soup_form.find('span', 'pa_price')
            if not price:
                no_price_ = True
            else:
                loader.add_value('price', price.text)
        except:
            price = hxs.select('//div[@id="price"]//td[text()="Price:"]'
                               '/following-sibling::td/span/text()').extract()
            if not price:
                no_price_ = True
            else:
                loader.add_value('price', price[0])

        if no_price_:
            self.log('ERROR: no price found! URL:{}'.format(response.url))
            return

        reviews_url = hxs.select(u'//a[contains(text(),"customer review") and contains(@href, "product-reviews") '
                                 u'and not(contains(@href, "create-review"))]/@href').extract()
        loader.add_value('brand', response.meta['brand'].strip().lower())

        sku = hxs.select('//span[@class="tsLabel" and contains(text(), "Part Number")]/../span[2]/text()').extract()
        if not sku:
            sku = hxs.select('//b[contains(text(), "model number")]/../text()').extract()
        if sku:
            loader.add_value('sku', sku[0].strip().lower())
        else:
            self.log('ERROR: no SKU found! URL:{}'.format(response.url))

        identifier = hxs.select('//form/input[@name="ASIN"]/@value').extract()
        if not identifier:
            self.log('ERROR: no identifier found! URL:{}'.format(response.url))
            return
        else:
            loader.add_value('identifier', identifier)

        product_image = hxs.select('//*[@id="main-image" or @id="prodImage"]/@src').extract()
        if not product_image:
            self.log('ERROR: no product Image found!')
        else:
            image = urljoin_rfc(get_base_url(response), product_image[0].strip())
            loader.add_value('image_url', image)

        category = hxs.select('//*[@id="nav-subnav"]/li[1]/a/text()').extract()
        if not category:
            self.log("ERROR: category not found")
        else:
            loader.add_value('category', category[0].strip())

        product = loader.load_item()

        if product['identifier'] not in self.ids:
            self.ids.append(product['identifier'])

            metadata = KeterMeta()

            metadata['brand'] = response.meta['brand'].strip().lower()
            metadata['reviews'] = []
            product['metadata'] = metadata

            if reviews_url:
                yield Request(urljoin_rfc(base_url, reviews_url[0]), meta={'product': product}, callback=self.parse_review)
            else:
                yield product

    def parse_review(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        soup = BeautifulSoup(response.body)
        product = response.meta['product']

        reviews = hxs.select(u'//table[@id="productReviews"]//div[@style="margin-left:0.5em;"]')

        if not reviews:
            yield product
            return

        for review in reviews:
            loader = ReviewLoader(item=Review(), selector=hxs, date_format=u'%d/%m/%Y')
            date = review.select(u'.//nobr/text()')[0].extract()
            res = None
            date_formats = (u'%B %d, %Y', u'%d %b %Y', u'%d %B %Y')
            for fmt in date_formats:
                try:
                    res = time.strptime(date, fmt)
                except ValueError:
                    pass
                if res:
                    break
            date = time.strftime(u'%d/%m/%Y', res)
            loader.add_value('date', date)

            rating = review.select(u'.//text()').re(u'([\d\.]+) out of 5 stars')[0]
            rating = int(float(rating))
            loader.add_value('rating', rating)
            loader.add_value('url', response.url)

            title = review.select(u'.//b/text()')[0].extract()
            text = ''.join([s.strip() for s in review.select(u'div[@class="reviewText"]/text()').extract()])
            loader.add_value('full_text', u'%s\n%s' % (title, text))

            product['metadata']['reviews'].append(loader.load_item())

        next_page = soup.find('a', text=re.compile('Next'))
        if next_page and next_page.parent.get('href'):
            next_page = next_page.parent['href']
            yield Request(urljoin_rfc(base_url, next_page), meta=response.meta, callback=self.parse_review)
        else:
            yield product
