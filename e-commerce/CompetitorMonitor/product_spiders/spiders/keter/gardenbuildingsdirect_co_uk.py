# -*- coding: utf-8 -*-
import urlparse
import urllib
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from keteritems import KeterMeta, Review, ReviewLoader

from product_spiders.items import ProductLoader, Product
from product_spiders.spiders.siehunting.generic import GenericReviewSpider, xpath_select

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'

import re
price_re = re.compile("\d+\.?\d*")
review_date_format = re.compile(r"\d+/\d+/\d+")

def review_date_extractor(review_box):
    date_text = review_box.select('./td/div[1]//p//span/text()[2]').extract()
    if date_text:
        return date_text[0].split()[-1]

class GardenBuildingsDirectSpider(GenericReviewSpider):
    name = "gardenbuildingsdirect.co.uk"
    allowed_domains = ['gardenbuildingsdirect.co.uk']

    handle_httpstatus_list = [500]

    start_urls = [
        "http://www.gardenbuildingsdirect.co.uk/Search?y=0&x=0&q=Keter",
        "http://www.gardenbuildingsdirect.co.uk/Search?y=0&x=0&q=SUNCAST",
        "http://www.gardenbuildingsdirect.co.uk/Search?y=0&x=0&q=RUBBERMAID",
        "http://www.gardenbuildingsdirect.co.uk/Search?y=0&x=0&q=LIFETIME",
        "http://www.gardenbuildingsdirect.co.uk/Search?y=0&x=0&q=STEP2",
        "http://www.gardenbuildingsdirect.co.uk/Search?y=0&x=0&q=STERILITE"
    ]

    BRAND_GET_PARAM = "q"

    BRANDS = ['Keter', 'SUNCAST', 'RUBBERMAID', 'LIFETIME', 'STEP2', 'STERILITE']

    NAVIGATION = ['//div[@id="sub-nav-top"]//li[@class="next"]//a/@href', '//div[@id="product-list"]//a/@href']

    PRODUCT_BOX = [
        ('.', {'name': '//div[@id="product-options-container"]/h1[1]/text()',
               'price': ['//div[@class="price-container sale"]//span[contains(text(), "Now")]/text()', '//div[@class="price-container"]//span[contains(text(), "Now")]/text()', '//span[@class="option-price"]/text()'], 'sku': None, 'review_url': '//a[@class="view-al-test"]/@href'})
    ]

    PRODUCT_REVIEW_DATE_FORMAT = '%d/%m/%Y'
    PRODUCT_REVIEW_BOX = {'xpath': '//div[@class="boxproductinfo"]//table//tr', 'full_text': './td/div[2]/text()', 'date': review_date_extractor, 'rating': None, 'next_url': '//a[contains(text(),"Next") and contains(text(), "Page")]/@href'}

    def start_requests_(self):
        base_url = "http://www.gardenbuildingsdirect.co.uk/"
        for brand in self.BRANDS:
            url = urlparse.urljoin(base_url, "Search?" + urllib.urlencode({'x': 0, 'y': 0, 'q': brand}))
            yield Request(url, meta={'product_brand': brand})

    def parse_(self, response):
        brand = response.meta['brand']
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//div[@id="sub-nav-top"]//li[@class="next"]')
        if next_page:
            yield Request(urlparse.urljoin(base_url, next_page.select('.//a/@href').extract()[0]),
                                           meta={'brand': response.meta['brand']})

        for product_box in hxs.select('//div[@id="product-list"]/div'):
            product_name = product_box.select('.//div[@class="product-info"]//h3/a/text()').extract()[0]

            if not brand.upper() in product_name.upper():
                continue
            if not product_box.select('.//span[@class="price"]/text()').extract():
                continue

            product_url = product_box.select('.//div[@class="product-info"]//h3/a/@href').extract()[0]
            option_trows = product_box.select('.//table[@class="option-prices"]//tr')

            for option_tr in option_trows:
                if not option_tr.select('.//td[@class="option-name"]/text()'):
                    continue
                product_loader = ProductLoader(item=Product(), selector=option_tr)

                product_loader.add_value('url', product_url)
                option_name = option_tr.select('.//td[@class="option-name"]/text()').extract()[0]
                product_loader.add_value('name', product_name.strip() + " " + option_name.strip())
                product_loader.add_xpath('price', './/td[starts-with(@class,"option-price")]/text()')
                product_loader.add_value('brand', brand.lower())
                product = product_loader.load_item()
                product['metadata'] = KeterMeta()
                product['metadata']['brand'] = brand
                yield Request(product_url, callback=self.visit_product_page, meta={'product': product})
            else:
                product_loader = ProductLoader(item=Product(), selector=product_box)
                product_loader.add_value('name', product_name)
                product_loader.add_value('url', product_url)
                product_loader.add_value('brand', brand.lower())
                price = product_box.select('.//div[@class="price-container"]/span[@class="price"]/span/text()').extract()
                if price:
                    product_loader.add_xpath('price', './/div[@class="price-container"]/span[@class="price"]/span/text()')
                else:
                    product_loader.add_value('price', '0')
                product = product_loader.load_item()
                product['metadata'] = KeterMeta()
                product['metadata']['brand'] = brand
                yield Request(product_url, callback=self.visit_product_page, meta={'product': product})

    def visit_product_page_(self, response):
        product = response.meta['product']
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        reviews = hxs.select('//div[@id="reviews-container"]')
        if reviews:
            product['metadata']['reviews'] = []
            reviews_link = reviews.select('.//a[@class="view-al-test"]/@href')
            if reviews_link:
                yield Request(urlparse.urljoin(base_url, reviews_link.extract()[0]),
                              callback=self.process_product_reviews, meta={'product': product})
            #else:
            #    for review_box in reviews.select('.//div[@class="review_"]'):
            #        loader = ReviewLoader(item=Review(), selector=hxs, date_format='%m/%d/%Y')
            #        loader.add_value('rating', '')
            #        loader.add_value('date', '')
            #        loader.add_value('full_text', '')
            #        loader.add_value('url', '')
            #        product['metadata']['reviews'].append(loader.load_item())
            #    yield product
        else:
            yield product

    def process_product_reviews(self, response):
        hxs = HtmlXPathSelector(response)
        visited_reviews = response.meta.get('visited_reviews', set())
        product = response.meta['product']
        visited_reviews.add(response.url)
        base_url = get_base_url(response)
        for review_box in hxs.select('//div[@class="boxproductinfo"]//table//tr'):
            loader = ReviewLoader(item=Review(), selector=hxs, date_format='%d/%m/%Y')
            date = review_date_format.findall(review_box.select("./td/div[1]//p//span/text()").extract()[1])
            if date:
                loader.add_value('date', date[0])
            loader.add_value('full_text', review_box.select("./td/div[2]/text()").extract()[0].strip('" \r\n"'))
            loader.add_value('url', response.url)
            product['metadata']['reviews'].append(loader.load_item())

        for link in hxs.select('//table[@class="pricingbox"]//a/@href').extract():
            next_page = urlparse.urljoin(base_url, link)
            if "productreviews" in link and not next_page in visited_reviews:
                yield Request(next_page, callback=self.process_product_reviews,
                              meta={'product': product, 'visited_reviews': visited_reviews})
                return
        yield product

    def after_product_parse(self, response, product_box, product, product_box_spec):
        base_url = self.get_base_url(response)
        response.meta.update({'product': product})

        review_urls = product_box_spec.get('review_url', []) if hasattr(product_box_spec.get('review_url', []), 'append') else [product_box_spec['review_url']] if callable(product_box_spec.get('review_url')) else [product_box_spec['review_url']]

        if not any(review_urls):
            yield self.clean_product(product)

        reviews_available = []
        for xpath in review_urls:
            if xpath == '.' or not xpath:
                # reviews are available in the product page

                for item in self.parse_product_reviews(response):
                    yield item
                reviews_available.append(True)
            else:
                review_url = xpath_select(product_box, xpath).extract() if not callable(xpath) else [xpath(product)]
                if review_url:
                    url = urlparse.urljoin(base_url, review_url[0])
                    if not url in self.visited_urls:
                        self.visited_urls.add(url)
                        yield Request(url=url, callback=self.parse_product_reviews, dont_filter=True, meta=dict(**response.meta))
                    reviews_available.append(True)
                else:
                    reviews_available.append(False)

        if not any(reviews_available):
            yield self.clean_product(product)
