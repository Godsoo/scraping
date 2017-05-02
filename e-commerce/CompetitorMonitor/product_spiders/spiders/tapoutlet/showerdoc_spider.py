import re
import json
from decimal import Decimal
import os

# from scrapy.spider import BaseSpider
from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip\
                             as ProductLoader
from urllib import urlencode

HERE = os.path.abspath(os.path.dirname(__file__))


class ShowerDocSpider(SitemapSpider):

    name = 'showerdoc.com'
    allowed_domains = ['showerdoc.com']
    # start_urls = ('http://www.showerdoc.com',)

    sitemap_urls = ['http://www.showerdoc.com/sitemap.xml']
    sitemap_rules = [
        ('/', 'parse_product'),
    ]

    # download_delay = 0.1

    def start_requests(self):
        for req in list(super(ShowerDocSpider, self).start_requests()):
            yield req

        yield Request('http://www.showerdoc.com/search?ss=%%', callback=self.parse_search)

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[contains(@class, "basic-search")]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product)

        for url in hxs.select('//div[@class="pager"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_search)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@id="ctrHeader_pnlMenu"]//a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url)

        sub_categories = hxs.select('//ul[li/a[contains(text(), "by Category")]]/li/div/ul/li/a/@href').extract()
        sub_categories += hxs.select('//div[@class="filter-sidebar"]//a/@href').extract()
        for sub_category in sub_categories:
            url = urljoin_rfc(get_base_url(response), sub_category)
            yield Request(url)

        product_lists = hxs.select('//div[@class="product-link"]/a/@href').extract()
        for product_list in product_lists:
            url = urljoin_rfc(get_base_url(response), product_list)
            yield Request(url, callback=self.parse_products)

        products = hxs.select('//table[@class="rgMasterTable"]/tbody/tr/td/a[@class="sparegrid"]/@href').extract()
        products += hxs.select('//div[@class="pl-product-link"]/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

        if not products:
            dep = hxs.select('//input[contains(@name, "hidDepartmentName")]/@value').extract()
            cat = hxs.select('//input[contains(@name, "hidCategoryName")]/@value').extract()
            params = {'category': "'" + cat[0] + "'" if cat else "''",
                      'department': "'" + dep[0] + "'" if dep else "''"}
            if dep or cat:
                url = 'http://www.showerdoc.com/odata/ProductDataService.svc/GetProductsByDepartmentAndCategoryAndRange?%s' % urlencode(params)
                yield Request(url, callback=self.parse_json_list)

    def parse_products(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//table[@class="rgMasterTable"]/tbody/tr/td/a[@class="sparegrid"]/@href').extract()
        products += hxs.select('//div[@class="pl-product-link"]/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

        if not products:
            identifier = hxs.select(u'//td[contains(text(), "Item\xa0Number:")]/span/text()').extract()[0]
            if identifier:
                yield Request(response.url, dont_filter=True, callback=self.parse_product)
            else:
                dep = hxs.select('//input[@id="ctl00_etradesearch1_hidDepartmentName"]').extract()
                cat = hxs.select('//input[@id="ctl00_etradesearch1_hidCategoryName"]').extract()
                if dep and cat:
                    url = "http://www.showerdoc.com/odata/ProductDataService.svc/GetProductsByDepartmentAndCategoryAndRange?department='" + dep[0] + "'&category='" + cat[0] + "'"
                    yield Request(url, callback=self.parse_json_list)


    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        try:
            name = hxs.select('//div[@class="product-info"]/h1/text()').extract()[0]
        except:
            return
        loader = ProductLoader(item=Product(), response=response)
        try:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response),
                hxs.select('//div[@id="galleryImages"]/a/@data-image').extract()[0]))
        except:
            pass
        try:
            category = hxs.select('//div[@class="bread"]/a/text()').extract()[-1]
            loader.add_value('category', category)
        except:
            pass
        loader.add_xpath('brand', '//div[@class="product-info"]/div[@class="product-manufacturer"]/img/@alt')
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        identifier = hxs.select(u'//span[@id="ctl05_Product1_lbItemNumber"]/text()').extract()[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier.partition('-')[-1].replace(' ', ''))
        price = hxs.select('//div[@class="price"]/span[@class="priceinfo"]/text()').extract()
        if price:
            price = price[0]
            loader.add_value('price', self.calculate_price(price))
            yield loader.load_item()

    def parse_json_list(self, response):
        result = response.body.split('">')[-1].split('</')[0]
        products = json.loads(result)
        for product in products:
            url = urljoin_rfc(get_base_url(response), product.get('oDataSourceURL'))
            yield Request(url, callback=self.parse_product)

    def calculate_price(self, value):
        res = re.search(r'[.0-9]+', value)
        if res:
            price = Decimal(res.group(0))
            self.log("Price: %s" % price)
            return round((price) / Decimal('1.2'), 2)  # 20% EXC VAT
        else:
            return None
