import os
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

HERE = os.path.abspath(os.path.dirname(__file__))

class CharterhouseAquaticsSpider(BaseSpider):
    name = 'charterhouse-aquatics.co.uk'
    allowed_domains = ['charterhouse-aquatics.co.uk']
    start_urls = ['http://www.charterhouse-aquatics.co.uk/']
    brand_crawled = False

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@class="cbp-hrsub-inner"]/div/ul/li/a/@href').extract()
        #categories += hxs.select('//ul[@class="mega-menu"]/li/a/@href').extract()
        for url in categories:
            #if not re.search('^http', url):
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        if not self.brand_crawled:
            brands = hxs.select('//*[@class="infoBox-categories"]//a/@href').extract()
            for url in brands:
                if not re.search('^http', url):
                    url = urljoin_rfc(base_url, url)
                yield Request(url, callback=self.parse_products)
            self.brand_crawled = True

        # Is it another subcategory page?
        sub_sub_categories = hxs.select('//*[@class="infoBox_element"]/a/@href').extract()
        sub_sub_categories += hxs.select('//div[@id="catView"]//a/@href').extract()
        for url in sub_sub_categories:
            if not re.search('^http', url):
                url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_products)

        # Is it products page?
        products = hxs.select('//div[@id="productView"]/ul/li[@class="product"]')
        for product in products:
            try:
                url = product.select('.//h2/a/@href').extract().pop()
                yield Request(urljoin_rfc(base_url, url),
                              callback=self.parse_product)
            except:
                pass

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            identifier = hxs.select('//*[@class="buyButton"]/a/@onclick')\
                .re(r'^.+\((.+)\)')[0].split(',')[0]
        except:
            identifier = re.findall(r'^http.+p-(\d+)\.html$', response.url)[0]
        name = hxs.select('//div[@class="description"]/h2/text()').extract()[0]
        try:
            category = hxs.select('//div[@class="back"]/a/text()').extract()[0]
        except:
            category = u''
        image_url = hxs.select('//div[@class="image"]/div[@class="large"]/a'
                               '/img/@src').extract()
        if not image_url:
            image_url = hxs.select('//*[@class="image"]//*[@class="large"]//img/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
        else:
            image_url = u''

        try:
            price = hxs.select('//*[@class="productSpecialPrice"]/text()').extract()[0]
        except:
            price = hxs.select('//*[@class="price"]/text()').extract()
            if price:
                price = price[0]
            else:
                price = 0

        # Add values
        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('category', category)
        loader.add_value('image_url', image_url)
        loader.add_value('price', price)
        yield loader.load_item()
