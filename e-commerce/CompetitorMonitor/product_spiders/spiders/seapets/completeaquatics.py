from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import logging as log


class OnlineShoesSpider(BaseSpider):
    name = 'completeaquatics.co.uk'
    allowed_domains = ['www.completeaquatics.co.uk', 'completeaquatics.co.uk']
    start_urls = ['http://completeaquatics.co.uk']

    page_suffix = "page%d.html"
    per_page = 40

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select(
            '//div[@id="panel-navigation"]/a[@class="link-department"]/@href')

        for cat in categories.extract():
            yield Request(cat, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        # handle current page
        for p in self.get_products_from_page(response):
            yield p
        # handle other pages
        total_count = hxs.select("//span[@class='total-count']/text()").extract()
        if not total_count:
            log.error("Products count not found %s" % response.url)
            return
        total_count = total_count[0]
        pages_count = int(total_count) / self.per_page + 1
        for page_index in xrange(1, pages_count + 1):
            url = urljoin_rfc(response.url, self.page_suffix % page_index)
            yield Request(
                url,
                callback=self.get_products_from_page
            )

    def get_products_from_page(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select(
            ("//div[@class='catproducts']//"
             "div[@class='prodlistboxbg']//a/@href")).extract()
        for prod_url in products:
            yield Request(
                prod_url,
                self.parse_product
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select("//div[@class='crumb_trail']/text()").extract()
        if not name:
            log.error("No product name! %s" % base_url)
            return
        name = name[-1].strip()

        price = hxs.select("//div[@class='productheader']/span[@class='text-pricespecial']/text() | "
                           "//div[@class='productheader']/span[@class='text-price']/text()").extract()
        if not price:
            log.error("No product price! %s" % base_url)
            return
        price = price[0]

        loader = ProductLoader(response=response, item=Product())
        loader.add_value("name", name)
        loader.add_value("url", base_url)
        loader.add_value("price", price)
        loader.add_xpath('sku', "//input[@name='prodcode']/@value")
        loader.add_xpath('identifier', "//input[@name='prodcode']/@value")
        yield loader.load_item()
