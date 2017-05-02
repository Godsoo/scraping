import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price

def extract_price(s):
    price = re.search('([\d\.,]+)', s) or ''
    if price:
        price = price.groups()[0]
    price = price.replace(',', '')
    return price

class CakeStuffSpider(BaseSpider):
    name = 'cakestuff'
    allowed_domains = ['cake-stuff.com']
    start_urls = ('http://www.cake-stuff.com/search/all-products?page_type=productlistings&page_variant=show&show=240',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #parse categories
        urls = hxs.select('//div[contains(@class,"product product")]//a[@class="product_options_view"]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        #parse pagination
        urls = hxs.select('//div[@class="pages"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_name = hxs.select('//*[@id="product_title"]/text()').extract()[0]
        image_url = hxs.select('//*[@id="product_medium_image"]//@src').extract()[0]
        product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        product_loader.add_value('name', product_name)
        product_loader.add_value('url', response.url)
        identifier = hxs.select('//*[@id="parent_product_id"]//@value').extract()
        product_loader.add_value('identifier', identifier[0])
        product_loader.add_value('sku', '')
        price = hxs.select('//*[@id="price_break_1"]//span[@class="GBP"]/@content').extract()[0]
        product_loader.add_value('price', extract_price(price))
        out_of_stock = hxs.select('//*[@id="out_of_stock_sash"]').extract()
        if out_of_stock:
            product_loader.add_value('stock', 0)
        category = hxs.select('//*[@id="breadcrumb_container"]/p/span[2]/a/text()').extract()
        if category:
            product_loader.add_value('category', category[0])
        product = product_loader.load_item()
        
        bulks = response.xpath('//div[@id="product_price_breaks"]//th/text()').extract()
        prices = map(extract_price, response.css('div#product_price_breaks span.price span.inc span.GBP::text').extract())
        bulk_prices = ', '.join('%s: %s' % (bulk, price) for (bulk, price) in zip(bulks, prices))
        if bulk_prices:
            product['metadata'] = {'bulk_prices': bulk_prices}
        yield product