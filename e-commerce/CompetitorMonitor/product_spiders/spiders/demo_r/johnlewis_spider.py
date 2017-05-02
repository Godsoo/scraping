import os
import csv
import shutil
from scrapy import signals
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from demoritems import DemoRMeta

HERE = os.path.abspath(os.path.dirname(__file__))

class JohnLewisSpider(BaseSpider):
    name = 'demo_r-johnlewis.com'
    allowed_domains = ['johnlewis.com']
    start_urls = ['http://www.johnlewis.com']

    def start_requests(self):
        country_url = "http://www.johnlewis.com/store/international/ajax/changeCountryAjaxRequest.jsp"
        formdata = {'country': 'GB',
                    'sourceUrl': 'http://www.johnlewis.com/',
                    'switchToggle': 'Change Country Overlay'}
        yield FormRequest(country_url, formdata=formdata, callback=self.parse_country)

    def parse_country(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//div[strong[contains(text(), "Computing")] or strong[contains(text(), "Smart Tech & Phones")] or strong[contains(text(), "Sound & Vision")]]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        for cat in response.xpath('//section[contains(@class, "lt-nav-container-links")]//a/@href').extract():
            if '/electricals/' in cat:
                yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse)
        for url in response.xpath('//div[@class="result-row"]/article/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_products)
        next = response.xpath('//li[@class="next"][1]/a/@href').extract()
        if next:
            yield Request(url=urljoin_rfc(base_url, next[0]))

    def parse_products(self, response):
        base_url = get_base_url(response)

        products_urls = response.xpath('//*[@id="prod-product-colour"]/ul//li//a/@href').extract()
        if products_urls:
            for url in products_urls:
                purl = urljoin_rfc(base_url, url)
                yield Request(
                    url=purl,
                    callback=self.parse_product)
        else:
            for p in self.parse_product(response):
                yield p

    def parse_product(self, response):
        base_url = get_base_url(response)

        product_code = response.xpath('//div[@id="prod-product-code"]/p/text()').extract()

        if not product_code:
            return

        name = response.xpath('//*[@id="prod-title"]//text()').extract()
        if not name:
            name = response.xpath('//*[@id="content"]//h1/text()').extract()
            if not name:
                return

        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])

        loader = ProductLoader(item=Product(), response=response)

        loader.add_value('identifier', product_code)
        loader.add_value('sku', product_code)
        loader.add_value('url', response.url)
        loader.add_value('name', ' '.join([n.strip() for n in name]).strip())
        loader.add_xpath('category', '//div[@id="breadcrumbs"]/ol/li[position()>1 and position()<last()]//a/text()')
        loader.add_xpath('price', '//span[@itemprop="price"]/text()|//div[@id="prod-add-to-basket"]//strong[@class="price"]/text()', re=r'[\d,.]+')
        loader.add_value('image_url', image_url)
        loader.add_xpath('brand', 'normalize-space(//div[@itemprop="brand"]/span/text())')
        try:
            loader.add_xpath('stock', '//div[@data-jl-stock]/@data-jl-stock')
        except ValueError:
            loader.add_value('stock', '0')


        meta = DemoRMeta()
        meta['promotion'] = ''.join(response.xpath('//a[@href="tabinfo-spcl-offr"]/text()').extract())

        item = loader.load_item()
        item['metadata'] = meta

        if item['identifier']:
            yield item
