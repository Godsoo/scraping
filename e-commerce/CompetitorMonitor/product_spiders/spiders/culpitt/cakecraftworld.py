from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price


class CakecraftworldSpider(BaseSpider):
    name = 'cakecraftworld'
    allowed_domains = ['cakecraftworld.co.uk']
    start_urls = ('http://www.cakecraftworld.co.uk/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        urls = hxs.select('//li[@class="menu-item"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//ul[@class="sub-page-gallery clearfix"]//li/a/@href').extract()
        for url in urls:
            if not url.endswith('.pdf'):
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_list)
        urls = hxs.select('//ul[@id="prod-list"]//a[@class="button more-info"]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_name = hxs.select('//*[@class="product"]/h1/text()').extract()[0]
        image_url = hxs.select('//div[@id="thumbs"]//a[@class="thumb"]/@href').extract()
        identifier = hxs.select('//*[@id="page-content"]/form/input[@name="prodid"]/@value').extract()[0]
        category = hxs.select('//p[@id="breadcrumb"]/a[2]/text()').extract()

        options = hxs.select('//*[@id="prod-details"]/table[@class="product-options"]/tr[td]')
        if not options:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('name', product_name)
            product_loader.add_value('url', response.url)
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('sku', identifier)
            price = hxs.select('//span[@class="price" or @class="price so-price"]/em/text()').extract()[0]
            product_loader.add_value('price', extract_price(price))
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            if category:
                product_loader.add_value('category', category[0])
            out_of_stock = hxs.select('//*[@id="prod-details"]//h4[@class="outofstock"]').extract()
            if out_of_stock:
                product_loader.add_value('stock', 0)
            skip = False
            poa = hxs.select('//*[@id="prod-details"]//p[@class="product_order_button"]//text()').extract()
            if poa:
                if poa[0].strip() == 'Please phone for more details.':
                    skip = True
            if not skip:
                product = product_loader.load_item()
                yield product
        else:
            for option in options:
                product_loader = ProductLoader(item=Product(), selector=option)
                try:
                    code = option.select('.//input[@name="options"]/@value').extract()[0].strip()
                except IndexError:
                    continue
                option_name = option.select('.//span[@class="option-value"]/text()').extract()[0].strip()
                product_loader.add_value('name', product_name + ' - ' + option_name)
                product_loader.add_value('url', response.url)
                product_loader.add_value('identifier', identifier + '-' + code)
                product_loader.add_value('sku', identifier)
                try:
                    price = option.select('./td[2]/text()').extract()[0].strip()
                except:
                    price = option.select('.//span[@class="option-details"]/text()').extract()[0].strip()
                product_loader.add_value('price', extract_price(price))
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                if category:
                    product_loader.add_value('category', category[0])
                out_of_stock = option.select('.//span[@class="option-out-of-stock"]').extract()
                if out_of_stock:
                    product_loader.add_value('stock', 0)
                product = product_loader.load_item()
                yield product
