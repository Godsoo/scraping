import os
import csv


import time
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from keteritems import KeterMeta, Review, ReviewLoader
from product_spiders.spiders.BeautifulSoup import BeautifulSoup
import re
import json

from scrapy import log

from scrapy.utils.response import open_in_browser

HERE = os.path.abspath(os.path.dirname(__file__))


class CdiscountSpider(BaseSpider):
    handle_httpstatus_list = [404]
    name = u'husqvarna_cdiscount.com'
    allowed_domains = ['cdiscount.com']
    start_urls = [
        u'http://www.cdiscount.com/search/10/flymo.html',
        u'http://www.cdiscount.com/search/10/mc+culloch.html',
        u'http://www.cdiscount.com/search/10/gardena.html',
    ]
    errors = []
    brands = set()
    
    def __init__(self, *args, **kwargs):
        super(CdiscountSpider, self).__init__(*args, **kwargs)
        with open(HERE+'/brands.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.brands.add(row['brand'].replace(' ', '').title())        

    def start_requests(self):
        search_url = u'http://www.cdiscount.com/search/10/%s.html'
        brands = {}

        with open(HERE+'/brands.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                brands[row['brand']] = search_url % row['brand'].lower().replace(' ','+')
                self.brands.add(row['brand'].replace(' ', '').title())
    
        for brand, url in brands.items():
            yield Request(url, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        items = hxs.select('//div[@id="lpContent"]/ul/li[div/a]')
        items += hxs.select('//li[@data-sku]')
        if not items:
            retries = response.meta.get('retries', 0)
            if retries < 6:
                meta = response.meta
                meta['retries'] = retries + 1
                yield response.request.replace(dont_filter=True, meta=meta)
            return
        
        for item in items:
            url_sellers = item.select('div/form/div/div[@class="facMkt"]/a/@href').extract()
            main_url = item.select('div/a/@href').extract()[0].replace("#/", "/")
            if url_sellers:
                url = url_sellers[0].replace("#/", "/")
                alternative_url = urljoin(base_url, main_url)
            else:
                url = main_url
                alternative_url = None
            price = self.parse_price(item.select('div/form/div/div/span[@class="price"]//text()').extract())
            yield Request(urljoin(base_url, url),
                          callback=self.preparse_product,
                          meta={'price': price,
                                'alternative_url': alternative_url})

        pages = hxs.select('//input[@id="PaginationForm_TotalPage"]/@value').extract()
        curr_page = hxs.select('//input[@id="PaginationForm_CurrentPage"]/@value').extract()
        if pages and curr_page:
            try:
                pages = int(pages.pop())
                curr_page = int(curr_page.pop())
                if curr_page < pages:
                    yield Request(base_url.split("?")[0] + "?page=%d" % (curr_page + 1), callback=self.parse)
            except (ValueError, TypeError):
                pass

    def parse_price(self, price):
        if price and isinstance(price, list):
            price = ".".join(price)
        elif not price:
            return None
        price = price.replace(",", ".").strip().replace(u"\xa0", "").replace(u"\u20ac", "")
        try:
            price, count = re.subn(r'[^0-9 .,]*([0-9 .,]+)[^0-9 .,]*', r'\1', price)
        except TypeError:
            return None
        if count:
            price = price.replace(" ", "")
            try:
                price = float(price)
            except ValueError:
                return None
            else:
                return price
        elif price.isdigit():
            return float(price)
        return None

    def create_review_loader(self, response, data):
        fields = ['url', 'date', 'rating', 'product_url', 'sku', 'full_text']
        loader = ReviewLoader(item=Review(), response=response, date_format=u'%d/%m/%Y')
        for key, value in data.items():
            if key in fields:
                loader.add_value(key, value)
        return loader.load_item()

    def create_product_loader(self, response, data):
        fields = ['url', 'name', 'category', 'identifier', 'sku', 'price', 'stock', 'image_url', 'brand', 'dealer', 'shipping_cost']
        loader = ProductLoader(response=response, item=Product())
        for key, value in data.items():
            if key in fields:
                loader.add_value(key, value)
        return loader.load_item()

    def preparse_product(self, response):
        return self.parse_product(response)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        data = {}
        data['url'] = urljoin(base_url, response.url)


        name = hxs.select('//h1[contains(@class ,"MpProductTitle")]/text()').extract()
        if not name:
            name = hxs.select('//h1[@itemprop="name"]/text()').extract()
            if not name:
                name = hxs.select('//div[@class="fpZnPrd"]/h1/text()').extract()
                if not name:
                    name = hxs.select('//div[@class="fpmTDesc"]/h1/text()').extract()

        if name:
            data['name'] = name[0].strip()
        else:
            self.log('Product without name')
            self.log('Retrying %s' %response.url)
            tries = response.meta.get('tries', 0)
            if tries < 6:
                meta = response.meta
                meta['tries'] = tries + 1
                yield response.request.replace(meta=meta, dont_filter=True)
            return

        category = hxs.select('//div[@id="bc"]/nav/ul/li/a/text()').extract()
        data['category'] = category.pop() if category else ''

        data['sku'] = hxs.select('//input[@id="sku"]/@value').extract().pop()

        more_sellers_link = hxs.select('//p[@id="mpOffer"]').extract()
        if more_sellers_link:
            dep_id = hxs.select('//input[@id="depId"]/@value').extract()[0]
            sellers_url = 'mp-'+dep_id+'-'+data['sku'].upper()+'.html?Filter=New'
            sellers_url = urljoin(base_url, sellers_url)
            yield Request(sellers_url,
                          callback=self.preparse_product,
                          meta={'price': '',
                                'alternative_url': ''})
            return
            

        # data['price'] = self.parse_price(hxs.select('//ins[@itemprop="price"]/text()').extract().pop())

        brand = response.xpath('//span[@itemprop="brand"]/a/@title').extract() or response.xpath('//img[@class="fpmBrand"]/@title').extract()
        if brand:
            data['brand'] = brand.pop()
            if data['brand'].replace(' ', '').title() not in self.brands:
                self.log('No brand found in the feed file for %s. Ignoring the product.' %response.url)
                return
        elif response.meta.get('brand'):
            data['brand'] = response.meta['brand']

        try:
            data['image_url'] = urljoin(base_url, hxs.select('//noscript/a/img/@src').extract().pop())
        except IndexError:
            try:
                data['image_url'] = urljoin(base, hxs.select('//img[@itemprop="image"]/@src').extract().pop())
            except:
                # self.errors.append("No image set for url: '%s'" % urljoin(base_url, response.url))
                pass

        sellers = hxs.select('//div[@id="OfferList"]/div')
        reviews = hxs.select('//div[@class="detMainRating"]/div[contains(@class, "detRating")]')
        if sellers:
            for dealer in sellers:
                dealer_name = (dealer.select('div/div/div/div/div/a/@title').extract() or ["CDiscount"]).pop()
                shipping_cost = self.parse_price(dealer.select('div//div[@class="DeliveryMode"]/span[@class="ColPlContent"]/text()').extract())
                price = dealer.select('div//div[@class="priceContainer"]/div[contains(@class, "price")]//text()').extract()
                if shipping_cost:
                    data['shipping_cost'] = shipping_cost
                elif 'shipping_cost' in data:
                    del data['shipping_cost']
                data['dealer'] = dealer_name
                data['identifier'] = data['sku'] + dealer_name
                data['price'] = self.parse_price(price)
                product = self.create_product_loader(response, data)

                if reviews:
                    metadata = KeterMeta()
                    metadata['reviews'] = []
                    if brand:
                        metadata['brand'] = data['brand']
                    for review in reviews:
                        review_data = {}
                        review_data['rating'] = review.select('div//div[@class="rat"]/span/text()').extract()[0]
                        review_date = review.select('div//div[@class="date"]/@content').extract().pop()
                        review_data['date'] = time.strftime('%d/%m/%Y', time.strptime(review_date, "%Y-%m-%d"))
                        review_data['product_url'] = data['url']
                        review_data['sku'] = data['sku']
                        review_title = review.select('div//div[@class="title"]/span/text()').extract()
                        review_text = review.select('div//div[@class="comm"]/text()').extract()
                        review_data['full_text'] = "\n".join(review_title + review_text)
                        metadata['reviews'].append(self.create_review_loader(response, review_data))
                    product['metadata'] = metadata
                yield product
            # Next page?
            next_page = hxs.select(u'//ul[@class="PaginationButtons"]//a[contains(text(),"Suivant")]')
            if next_page:
                next_page_onclick_id = next_page.select('@id').extract()[-1] + '.OnClick'
                yield FormRequest.from_response(response, formname='PageForm', formdata={next_page_onclick_id: u'1'},
                    callback=self.parse_product, meta=response.meta, dont_filter=True)
        else:
            # The website has changed but in some offer pages keep the old structure.
            sellers = hxs.select('//div[@id="fpmContent"]/div[contains(@class, "fpBlk")]')
            reviews_url = hxs.select('//div[@class="fpmTDReview"]/a[@class="fpProdRateStars"]/@href').extract()
            if sellers:
                for seller in sellers:
                    seller_name = seller.select('div[@class="fpSlrName"]/a[@class="slrName"]/text()').extract()
                    dealer_name = seller_name[0].strip() if seller_name else 'Cdiscount'
                    seller_price = '.'.join(seller.select('.//p[@class="price"]//text()').re(r'(\d+)'))
                    if not seller_price:
                        continue
                    shipping = seller.select('./div[@class="fpSlrCom"]/table/tbody/tr/td[2]/span[@class="price"]/text()').re(r'([\d.,]+)')
                    shipping_cost = shipping[0].replace('.', ',').replace(',', '.') if shipping else '0.00'

                    data['shipping_cost'] = shipping_cost
                    data['dealer'] = dealer_name
                    data['identifier'] = data['sku'] + dealer_name
                    data['price'] = self.parse_price(seller_price)
                    product = self.create_product_loader(response, data)

                    if reviews_url:
                        url = urljoin(base_url, reviews_url[0])
                        yield Request(
                            url,
                            callback=self.parse_reviews,
                            meta={'product': product},
                            dont_filter=True,
                        )
                    else:
                        yield product

                # Next page
                params = {
                    'FiltersAndSorts.ChkFilterToNew': 'true',
                    'FiltersAndSorts.ChkSortByPriceAndShipping': 'true',
                }
                pagination_params = dict(
                    zip(hxs.select('//input[contains(@name, "Pagination.")]/@name').extract(),
                        hxs.select('//input[contains(@name, "Pagination.")]/@value').extract()))
                if pagination_params.get('Pagination.CurrentPage', 1) != pagination_params.get('Pagination.TotalPageCount', 1):
                        next_page = int(pagination_params.get('Pagination.CurrentPage', 1)) + 1
                        pagination_params['Pagination.CurrentPage'] = str(next_page)
                        params.update(pagination_params)
                        yield FormRequest(response.url,
                                          callback=self.parse_product,
                                          formdata=params,
                                          dont_filter=True,
                                          meta=response.meta)
            elif response.meta.get('alternative_url'):
                # This site have bugs and sometimes does not list the offers.
                meta = response.meta.copy()
                if data.get('brand'):
                    meta['brand'] = data['brand']
                meta['alternative_url'] = None
                yield Request(response.meta['alternative_url'],
                              callback=self.parse_product,
                              meta=meta)
            else:
                seller = hxs.select('//a[@href="#seller"]/text()').extract()
                if not seller:
                    seller = hxs.select('//script[contains(text(),"fpSellBy")]').re('.*>(.*?)</a')
                seller_name = seller[0] if seller else 'CDiscount'
                data['price'] = response.meta.get('price', 0)
                data['identifier'] = data['sku'] + seller_name
                data['dealer'] = seller_name
                try:
                    data['image_url'] = urljoin(base_url, hxs.select('//img[@class="jsSmallImg"]/@src').extract().pop())
                except IndexError:
                    # self.errors.append("No image set for url: '%s'" % urljoin(base_url, response.url))
                    pass
                product = self.create_product_loader(response, data)
                if reviews:
                    metadata = KeterMeta()
                    metadata['reviews'] = []
                    if brand:
                        metadata['brand'] = data['brand']
                    for review in reviews:
                        review_data = {}
                        review_data['rating'] = review.select('div//div[@class="rat"]/span/text()').extract()[0]
                        review_date = review.select('div//div[@class="date"]/@content').extract().pop()
                        review_data['date'] = time.strftime('%d/%m/%Y', time.strptime(review_date, "%Y-%m-%d"))
                        review_data['product_url'] = data['url']
                        review_data['sku'] = data['sku']
                        review_title = review.select('div//div[@class="title"]/span/text()').extract()
                        review_text = review.select('div//div[@class="comm"]/text()').extract()
                        review_data['full_text'] = "\n".join(review_title + review_text)
                        metadata['reviews'].append(self.create_review_loader(response, review_data))
                    product['metadata'] = metadata
                yield product


    def parse_reviews(self, response):
        hxs = HtmlXPathSelector(response)

        product = response.meta['product']
        reviews = hxs.select('//div[@class="detMainRating"]/div[contains(@class, "detRating")]')
        if reviews:
            metadata = KeterMeta()
            metadata['reviews'] = []
            metadata['brand'] = product.get('brand', '')
            for review in reviews:
                review_data = {}
                review_data['rating'] = review.select('div//div[@class="rat"]/span/text()').extract()[0]
                review_date = review.select('div//div[@class="date"]/@content').extract().pop()
                review_data['date'] = time.strftime('%d/%m/%Y', time.strptime(review_date, "%Y-%m-%d"))
                review_data['product_url'] = product['url']
                review_data['sku'] = product['sku']
                review_title = review.select('div//div[@class="title"]/span/text()').extract()
                review_text = review.select('div//div[@class="comm"]/text()').extract()
                review_data['full_text'] = "\n".join(review_title + review_text)
                metadata['reviews'].append(self.create_review_loader(response, review_data))
            product['metadata'] = metadata

        yield product
