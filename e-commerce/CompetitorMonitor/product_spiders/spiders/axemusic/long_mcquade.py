import json
import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product
from axemusic_item import ProductLoader

from product_spiders.utils import extract_price


def make_https(url):
    ''' Site redirects all http requests to https even though all links on site are http
        Skip the extra redirect request!
    '''
    return url.replace('http://www.long-mcquade.com/', 'https://www.long-mcquade.com/')

class LongMcQuadeSpider(BaseSpider):
    name = "long-mcquade.com"
    allowed_domains = ["www.long-mcquade.com", ]
    start_urls = [
        "https://www.long-mcquade.com/",
    ]

    def __init__(self, *args, **kwargs):
        super(LongMcQuadeSpider, self).__init__(*args, **kwargs)
        self.errors = []
        self.identifiers = set()

    def retry(self, response, error="", retries=3):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls'].pop()
        else:
            url = response.request.url
        if retry < retries:
            retry = retry + 1
            meta['retry'] = retry
            meta['recache'] = True
            self.log('%s retry %d' % (error, retry))
            return Request(url, dont_filter=True, meta=meta, callback=response.request.callback)
        else:
            self.log('%s \n%s\n' % (error, response.body))
            self.errors.append(error)

    def parse(self, response):
        # Dive in categories
        cats = response.xpath('//ul[@class="first-ul"]//a/@href').extract()
        for cat in cats:
            yield Request(response.urljoin(cat))

        # Dive in next page, if it is
        next_page = response.xpath('//ul[contains(@class, "pagination")]//a[contains(span/text(), ">")]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]))

        # Dive in product
        products = response.xpath('//a[@class="products-item-link"]/@href').extract()
        for product in products:
            if "?page=group&GroupedParentID=" in product:
                yield Request(response.urljoin(product))
            else:
                yield Request(response.urljoin(product), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Fill up the Product model fields
        # identifier =
        url = response.url
        brand = ''.join(response.xpath('//span[@id="product-brand"]/text()').extract()).strip()
        name = ''.join(response.xpath('//span[@id="product-header-name"]/text()').extract()).strip()
        full_name = brand + ' - ' + name
        # The price can be tagged in either <b> or <span>, or None
        price = response.xpath('//span[@id="product-regular-price"]/text()').extract()
        if not price:
            price = response.xpath('//span[@id="product-sale-price"]/text()').extract()
            if not price:
                price = 0  # Call for pricing
        sku = response.xpath('//h2[@id="product-model"]/text()').extract()
        identifier = response.xpath('//span[@id="product-sku"]/text()').extract()
        category = response.xpath('//div[@class="products-bredcrumbs"]/a/text()').extract()
        if len(category) > 1:
            category = category[1]
        else:
            category = ""
        image_url = response.xpath('//img[@id="product-image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url.pop())


        l = ProductLoader(response=response, item=Product())
        l.add_value('url', url)
        l.add_value('name', name)
        l.add_value('price', price)
        l.add_value('sku', sku)
        l.add_value('identifier', identifier)
        l.add_value('category', category)
        if image_url:
            l.add_value('image_url', image_url)
        l.add_value('brand', brand)
        item = l.load_item()
        if item['identifier'] not in self.identifiers and item['price'] > 0:
            self.identifiers.add(item['identifier'])
            yield item

    def parse_option(self, response):
        item = response.meta['item']

        option = json.loads(response.body)
        item['name'] = option['name']
        item['sku'] = option['model']
        item['image_url'] = 'http://' + option['imageLg']
        item['price'] = extract_price(option['price'])
        if item['price'] > 0:
            yield item
