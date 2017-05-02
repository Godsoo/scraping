import os
import csv

from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http import FormRequest
from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class FurniturechoiceCoUkSpider(BaseSpider):
    name = 'furniturechoice.co.uk'
    allowed_domains = ['furniturechoice.co.uk']
    errors = []

    def __init__(self, *args, **kwargs):
        super(FurniturechoiceCoUkSpider, self).__init__(*args, **kwargs)
        self._brands = {}
        with open(os.path.join(HERE, 'fcbrands.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._brands[row['ProductCode'].lower()] = row['Supplier'].strip()

    def retry(self, response, error="", retries=3):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls']
        else:
            url = response.request.url
        if retry < retries:
            retry = retry + 1
            meta['retry'] = retry
            meta['recache'] = True
            return Request(url, dont_filter=True, meta=meta, callback=response.request.callback)
        else:
            self.errors.append(error)

    def start_requests(self):
        yield Request('http://www.furniturechoice.co.uk/', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[contains(@class, "HeaderNavigation")]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            if '/Bedroom-Furniture/' in url:
                yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@class="Paging"]/a[@class="next"]/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

        for url in hxs.select(u'//div[@class="LeftNav"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list)

        for url in hxs.select(u'//h2[@class="desc"]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

        for url in hxs.select('//div[@class="productVariantTypeOptions"]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        if "PVT-DRAWERS" in response.body and "options" not in response.meta:
            name = hxs.select('//li[@class="PVT-DRAWERS"]//select/@name').extract()
            if name:
                name = name.pop()
                options = hxs.select('//li[@class="PVT-DRAWERS"]//select[@name="%s"]/option[not(@selected)]/@value' % name).extract()
                for option in options:
                    yield FormRequest.from_response(response,
                                                formname='aspnetForm',
                                                formdata={name: option},
                                                callback=self.parse_product,
                                                meta={'options': 1})
        url = response.url.split('/')[-1]
        url = 'http://www.furniturechoice.co.uk/Bedroom-Furniture/' + url
        product_loader.add_value('url', url)
        name = hxs.select(u'//h1//text()')
        if not name:
            request = self.retry(response, "No name for product: " + response.url)
            if request:
                yield request
            return
        product_loader.add_value('name', name)
        product_loader.add_xpath('category', u'//div[@class="BreadCrumb"]/ol/li[2]/a/@title')
        img = hxs.select(u'//div[@class="ProdImages"]/a/img/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop()))

        product = product_loader.load_item()
        options = hxs.select(u'//div[contains(@class, "MainProds")]/ol/li')
        if not options:
            options = hxs.select(u'//div[@class="SingColl"]/div[contains(@class, "Prod")]')
        if options:
            if len(options) == 1:
                prod = Product(product)
                prod['name'] = hxs.select('//span[@class="ProductHeading"]/text()').extract().pop()
                prod['sku'] = hxs.select(u'normalize-space(substring-after(.//div[@class="code"]/text(), ":"))').extract().pop()
                prod['identifier'] = prod['sku']
                prod['price'] = extract_price(hxs.select(u'//span[@class="NowPrice"]/span[@class="PROP"]/text()').extract().pop())
                prod['brand'] = self._brands.get(prod['sku'].lower(), '')
                if not prod['brand']:
                    self.log('WARNING! - NOT PRODUCT BRAND | SKU: %s' % prod['sku'])
                if prod['identifier']:
                    yield prod
            else:
                for opt in options:
                    prod = Product(product)
                    prod['name'] = opt.select(u'normalize-space(.//h2/text())').extract()[0]
                    prod['sku'] = opt.select(u'normalize-space(substring-after(.//div[@class="code"]/text(), ":"))').extract()[0]
                    prod['identifier'] = prod['sku']
                    prod['price'] = extract_price(opt.select(u'.//span[@class="Price"]/text()').extract()[0])

                    prod['brand'] = self._brands.get(prod['sku'].lower(), '')

                    if not prod['brand']:
                        self.log('WARNING! - NOT PRODUCT BRAND | SKU: %s' % prod['sku'])

                    yield prod
