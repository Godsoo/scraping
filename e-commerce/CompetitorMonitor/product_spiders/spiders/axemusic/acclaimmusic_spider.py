import os
from itertools import izip_longest
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product
from axemusic_item import ProductLoader


class AcclaimMusicSpider(BaseSpider):
    name = 'acclaim-music.com'
    allowed_domains = ['acclaim-music.com']
    start_urls = ['http://www.acclaim-music.com/search.php?mode=search&page=1']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//ul[@id="search-results"]/li/span[@class="wrapper"]')

        for product in products:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', product.select('.//span[@class="product-title"]/a/text()').extract()[0])
            url = product.select('.//span[@class="product-title"]/a/@href').extract()[0]
            loader.add_value('url', url)
            try:
                loader.add_value('price', product.select('.//span[@class="product-ourprice"]/text()').extract()[0])
            except IndexError:
                loader.add_value('price', 0)
            yield Request(url, callback=self.parse_product, meta={'loader': loader})
        pages = hxs.select('//div[contains(@class, "nav-pages")][1]//a/@href').extract()
        if pages:
            url = urljoin_rfc(get_base_url(response), pages[-1])
            yield Request(url, callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = response.meta.get('loader')

        try:
            brand = hxs.select('//div[@id="location"]/span/a[@class="bread-crumb"]/span/text()').extract()[-2]
        except:
            brand = None
        try:
            category = hxs.select('//div[@id="location"]/span/a[@class="bread-crumb"]/span/text()').extract()[-1]
        except:
            category = None
        image_url = hxs.select('//div[@class="image-box"]/img/@src').extract()
        identifier = hxs.select('//input[@name="productid"]/@value').extract()[0]
        sku = hxs.select('//tr[td/text()="Model #"]/td[not(text()="Model #")]/text()').extract()
        if not sku:
            sku = hxs.select('//tr[td/text()="Model"]/td[not(text()="Model")]/text()').extract()
        if sku:
            loader.add_value('sku', sku[0].strip())
        loader.add_value('category', category.replace(' - ' + brand, '') if brand else category)
        loader.add_value('identifier', identifier)
        if brand:
            loader.add_value('brand', brand)
        loader.add_value('image_url', image_url)
        yield loader.load_item()



    def _grouper(self, n, iterable, fillvalue=None):
        '''
        grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx
        '''
        args = [iter(iterable)] * n
        return izip_longest(fillvalue=fillvalue, *args)
