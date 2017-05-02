from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
import re
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.contrib.loader.processor import TakeFirst, Compose

def onlyDecimal(a):
    price = float(re.sub(r'[^0-9.]', '', a))
    return round(price / 1.2, 2)  # exc. VAT


class DraperToolboxSpider(BaseSpider):
    name = 'drapertoolbox.co.uk'
    allowed_domains = ['www.drapertoolbox.co.uk']
    start_urls = ['http://www.drapertoolbox.co.uk/sitemap']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        pages = hxs.select('//div[@id="sitemap"]/ul//li[not(ul)]/a/@href').extract()

        for page in pages:
            yield Request(urljoin_rfc(base_url, page), callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        if not response.url.endswith('-0000'):
            yield Request(response.url, dont_filter=True, callback=self.parse_product)
            # yield self.parse_product(response)

        xpath_handlers = [
            # parse product page
            (self.parse_product, '//div[@class="listingProduct" and (div[@class="listingAction"]//input[@type="image"] or div[@class="listingAction"]/img[@alt="Currently Unavailable"]) ]/div[@class="listingData"]/a[1]/@href'),
            # parse options page
            (self.parse_product_options, '//div[@class="listingProduct"]/div[@class="listingAction" and a/img[@alt="View Options"]]/a/@href')
        ]
        for xpath_hnd in xpath_handlers:
            callback_method, xpath_str = xpath_hnd
            pages = hxs.select(xpath_str).extract()
            for page in pages:
                url = urljoin_rfc(base_url, page)
                yield Request(url, callback=callback_method)

    def parse_product_options(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        xpath_handlers = [
            # parse product page
            (self.parse_product, '(//table[@class="productOptions"])[1]//td/a[@class="productlink"]/@href')
        ]
        for xpath_hnd in xpath_handlers:
            callback_method, xpath_str = xpath_hnd
            pages = hxs.select(xpath_str).extract()
            for page in pages:
                yield Request(urljoin_rfc(base_url, page), callback=callback_method)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        options = hxs.select('(//table[@class="productOptions"])[1]//td/a[@class="productlink"]/@href').extract()
        if options:
            for option in options:
                yield Request(urljoin_rfc(base_url, option), callback=self.parse_product)
        else:
            loader = ProductLoader(response=response, item=Product())
            loader.add_xpath('price', '//td[@itemprop="price"]/span[@class="pricemain"]/text()', TakeFirst(), Compose(onlyDecimal))
            '''
            if hxs.select('//input[@type="hidden"][@name="PID"]/@value'):
                loader.add_xpath('identifier', '//input[@type="hidden"][@name="PID"]/@value')
            elif hxs.select('//input[@type="hidden"][@name="signupstockpid"]/@value'):
                loader.add_xpath('identifier', '//input[@type="hidden"][@name="signupstockpid"]/@value')
            else:
                self.log("NO IDENTIFIER!!!")
            '''
            loader.add_value('identifier', re.search(r'-(\d+)$', response.url).groups()[0])
            loader.add_xpath('sku', '//span[@itemprop="mpn"]/text()')
            loader.add_xpath('brand', '//div[@id="productBoxes"]/div[@class="productBox" and contains(p/text(), "Manufacturer")]/a/@href', re="w=(.*)")
            loader.add_value('url', urljoin_rfc(base_url, response.url))
            loader.add_xpath('name', '//div[@class="productTitle"]/h1/text()')
            loader.add_xpath('image_url', '(//div[@id="productImgFrame"]//img)[2]/@src')
            loader.add_xpath('category', '//div[@id="Breadcrumb"]/div/a[last()]/text()')
            yield loader.load_item()
