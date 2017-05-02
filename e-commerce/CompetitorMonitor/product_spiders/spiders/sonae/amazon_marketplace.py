# -*- coding: utf-8 -*-
import csv
import time
import os.path
from urlparse import urljoin
from datetime import datetime
from scrapy.utils.response import get_base_url
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.url import url_query_parameter
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraper, AmazonFilter, AmazonUrlCreator, AmazonScraperException
from product_spiders.base_spiders.amazonspider2.amazonspider_concurrent import BaseAmazonConcurrentSpider

HERE = os.path.abspath(os.path.dirname(__file__))

class SonaeAmazonScraper(AmazonScraper):
    def scrape_mbc_list_page(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        try:
            url = hxs.select('//a[@id="olpDetailPageLink"]/@href').extract()[0]
            url = urljoin(base_url, url)
            url_parts = url.split('/')
            try:
                asin = url_parts[url_parts.index('product') + 1]
            except ValueError:
                asin = url_parts[url_parts.index('dp') + 1]
        except IndexError:
            return None

        products = []
        for i, result in enumerate(hxs.select('//div[@id="olpOfferList"]//div[contains(@class, "olpOffer")]'), 1):
            product = {}

            name = ' '.join(hxs.select(u'//div[@id="olpProductDetails"]/h1//text()').extract()).strip()
            product['name'] = AmazonFilter.filter_name(name)

            brand = hxs.select(u'//div[@id="olpProductByline"]/text()').extract()
            if brand:
                product['brand'] = AmazonFilter.filter_brand(brand[0])

            price_el = result.select('.//span[contains(@class, "olpOfferPrice")]/text()')
            if not price_el:
                # check if there is text "Add to basket to check price"
                price_text = result.select('.//div[p[contains(@class, "olpShippingInfo")]]/text()').extract()[0].strip()
                if 'basket' in price_text.lower():
                    product['price'] = None
                else:
                    raise AmazonScraperException(
                        "Couldn't extract price from element %d from url %s" % (i, response.url))
            else:
                price = price_el.extract()[0].strip()
                product['price'] = self._extract_price(response.url, price)

            seller_id = None
            seller_urls = result.select(u'.//*[contains(@class, "olpSellerName")]//a/@href').extract()
            if seller_urls:
                seller_url_ = seller_urls[0]
                if 'seller=' in seller_url_:
                    seller_id = url_query_parameter(seller_url_, 'seller')
                else:
                    seller_parts = seller_url_.split('/')
                    try:
                        seller_id = seller_parts[seller_parts.index('shops') + 1]
                    except (IndexError, KeyError, ValueError):
                        # External website (link "Shop this website"?)
                        seller_id = url_query_parameter(seller_url_, 'merchantID')

            product['identifier'] = asin
            product['asin'] = asin
            if seller_id:
                product['seller_identifier'] = seller_id
                product['url'] = AmazonUrlCreator.build_url_from_asin_and_dealer_id(
                    AmazonUrlCreator.get_domain_from_url(response.url), asin, seller_id)
                product['seller_url'] = AmazonUrlCreator.build_vendor_url(
                    AmazonUrlCreator.get_domain_from_url(response.url), seller_id)
                # product['url'] = 'http://%s/gp/product/%s/?m=%s' % (self._get_domain_from_url(response.url), product_id, seller_id)
            else:
                product['seller_identifier'] = None
                product['url'] = AmazonUrlCreator.build_url_from_asin(
                    AmazonUrlCreator.get_domain_from_url(response.url), asin)
                product['seller_url'] = None
                # product['url'] = 'http://%s/gp/product/%s/' % (self._get_domain_from_url(response.url), product_id)

            shipping = result.select('.//span[@class="olpShippingPrice"]/text()').extract()
            if shipping:
                product['shipping_cost'] = shipping[0]

            image_url = hxs.select(u'//div[@id="olpProductImage"]//img/@src').extract()
            if image_url:
                product['image_url'] = urljoin(base_url, image_url[0])

            vendor = result.select(u'.//div[contains(@class, "olpSellerColumn")]//img/@title').extract()
            if not vendor:
                vendor = result.select(u'.//div[contains(@class, "olpSellerColumn")]//img/@alt').extract()
            if not vendor:
                vendor = result.select(u'.//*[contains(@class, "olpSellerName")]//a/b/text()').extract()
            if not vendor:
                vendor = result.select(u'.//*[contains(@class, "olpSellerName")]//span/a/text()').extract()
            if vendor:
                vendor = vendor[0]
                if vendor.lower().startswith('amazon'):
                    vendor = 'Amazon'
                else:
                    vendor = 'AM - ' + vendor
                product['vendor'] = vendor
            elif not seller_id:
                product['vendor'] = 'Amazon'
            else:
                product['vendor'] = None

            stock = result.select('.//div[contains(@class,"olpDeliveryColumn")]//text()').re('En Stock|En stock')
            if stock:
                product['unavailable'] = False

            products.append(product)

        next_url = hxs.select('//ul[@class="a-pagination"]/li[@class="a-last"]/a/@href').extract()
        next_url = urljoin(base_url, next_url[0]) if next_url else None

        current_page = hxs.select('//ul[@class="a-pagination"]/li[@class="a-selected"]/a/text()').extract()
        current_page = current_page[0] if current_page else None

        return {
            'next_url': next_url,
            'current_page': current_page,
            'products': products
        }


class AmazonSpider(BaseAmazonConcurrentSpider):
    name = 'sonae-amazon.es-marketplace'
    domain = 'amazon.es'

    type = 'search'

    scraper_class = SonaeAmazonScraper

    all_sellers = True
    collect_new_products = True
    collect_used_products = False
    _use_amazon_identifier = True
    collected_identifiers = set()
    collect_products_from_list = True
    exclude_sellers = ['Amazon']
    scrape_categories_from_product_details = True

    collect_reviews = False

    try_suggested = False
    do_retry = True
    rotate_agent = True

    root = HERE
    file_path = os.path.join(root, 'worten_products.csv')

    max_retry_count = 100

    concurrent_searches = 8

    def __init__(self, *args, **kwargs):
        super(AmazonSpider, self).__init__(*args, **kwargs)

        if datetime.now().day == 10:
            self.use_previous_crawl_cache = False

    def get_search_query_generator(self):
        with open(self.file_path) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                product = {'sku': row['sku']}
                yield row['sku'], product

    def match(self, meta, search_item, found_item):
        return True
