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


HERE = os.path.abspath(os.path.dirname(__file__))

class JohnLewisBaseSpider(BaseSpider):
    allowed_domains = ['johnlewis.com']
    start_urls = ['http://www.johnlewis.com/electricals/c500001']

    categories = []

    def crawl_category(self, cat1, cat2):
        for c in self.categories:
            if c[0].lower() == cat1 and (c[1].lower() == cat2 or not c[1]):
                return True

        return False

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
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[starts-with(@class, "nn-flyout-col")]')
        for cat in categories:
            category_name = cat.select('./strong/text()').extract()[0].strip().lower()
            subcategories = cat.select('.//li/a')
            for subcat in subcategories:
                url = subcat.select('./@href').extract()[0]
                name = subcat.select('./text()').extract()[0].strip().lower()
                if self.crawl_category(category_name, name):
                    yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        cat_path = response.url.split('/')[-2]
        for url in hxs.select('//div[@class="col-3 first lt-nav"]//a/@href').extract():
            if ('/' + cat_path + '/') in url:
                yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat)

        for url in hxs.select('//div[@class="result-row"]/article/a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_products)
        next = hxs.select('//li[@class="next"][1]/a/@href').extract()
        if next:
            yield Request(url=urljoin_rfc(base_url, next[0]), callback=self.parse_products)

    def parse_products(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        products_urls = hxs.select('//*[@id="prod-product-colour"]/ul//li//a/@href').extract()
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
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_code = hxs.select('//div[@id="prod-product-code"]/p/text()').extract()

        if not product_code:
            return

        name = hxs.select('//*[@id="prod-title"]//text()').extract()
        if not name:
            name = hxs.select('//*[@id="content"]//h1/text()').extract()
            if not name:
                return

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])

        loader = ProductLoader(item=Product(), selector=hxs)

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

        item = loader.load_item()

        if item['identifier']:
            yield item
