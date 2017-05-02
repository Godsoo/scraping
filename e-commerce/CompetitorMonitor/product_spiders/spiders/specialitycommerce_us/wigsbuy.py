from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import itertools


class WigsbuySpider(BaseSpider):
    name = 'wigsbuy.com'
    allowed_domains = ['shop.wigsbuy.com']
    start_urls = ['http://shop.wigsbuy.com/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="nav"]/ul/li/a/@href').extract()[1:]:
            if 's/Holiday-Sales/' not in url and 'c/about-wigs/' not in url:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        category = hxs.select('//*[@id="nav_bread_crumb"]/div[1]/b/text()').extract()[0]
        for url in hxs.select('//div[@class="garrery_01"]//a[@class="dname"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': category})
        for url in hxs.select('//*[@id="list_selects"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)

        product_name = ''.join(hxs.select('//h1/text()').extract()).strip()
        sku = hxs.select('//ul[@class="Item"]//span/text()').extract()[0].strip()
        img = hxs.select('//div[@class="lagerimg"]//img/@src').extract()
        category = ''.join(hxs.select('//*[@id="bnav"]/div[1]//text()').extract())
        category = ''.join(category.strip().split(u'\xa0')).split('>')[1:]
        price = hxs.select('//*[@id="infoprice"]/text()').extract()[0]
        price = extract_price(price)

        sizes = hxs.select('//div[@class="size"]//option[@class="optionprice"]')
        if sizes:
            colors = hxs.select('//div[@class="color"]//a')
            if colors:
                size_variations = []
                for size in sizes:
                    size_id = size.select('./@value').extract()[0]
                    size_name = size.select('./@data-name').extract()[0]
                    size_price = size.select('./@data-price').extract()[0]
                    size_variations.append([size_id, size_name, size_price])

                    color_variations = []
                    for color in colors:
                        color_id = color.select('./@vid').extract()[0]
                        color_name = color.select('./@val').extract()[0]
                        color_price = color.select('./@data-price').extract()[0]
                        color_variations.append([color_id, color_name, color_price])
                    options = itertools.product(size_variations, color_variations)

                    for option in options:
                        product_identifier = sku + '_' + str(option[0][0]) + '_' + str(option[1][0])
                        name = product_name + ' ' + str(option[0][1]) + ' ' + str(option[1][1])
                        loader = ProductLoader(item=Product(), selector=hxs)
                        loader.add_value('identifier', product_identifier)
                        loader.add_value('sku', sku)
                        loader.add_value('url', response.url)
                        loader.add_value('name', name)
                        loader.add_value('price', price + extract_price(option[0][2]) + extract_price(option[1][2]))
                        if img:
                            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
                        loader.add_value('category', category)
                        yield loader.load_item()
            else:
                for size in sizes:
                    size_id = size.select('./@value').extract()[0]
                    size_name = size.select('./@data-name').extract()[0]
                    size_price = size.select('./@data-price').extract()[0]
                    product_identifier = sku + '_' + str(size_id)
                    name = product_name + ' ' + str(size_name)
                    loader = ProductLoader(item=Product(), selector=hxs)
                    loader.add_value('identifier', product_identifier)
                    loader.add_value('sku', sku)
                    loader.add_value('url', response.url)
                    loader.add_value('name', name)
                    loader.add_value('price', price + extract_price(size_price))
                    if img:
                        loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
                    loader.add_value('category', category)
                    yield loader.load_item()
