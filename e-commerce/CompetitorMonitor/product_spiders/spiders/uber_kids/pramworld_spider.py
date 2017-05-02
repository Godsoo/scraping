from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.spider import BaseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class PramWorldSpider(BaseSpider):
    name = 'uberkids-pramworld.co.uk'
    allowed_domains = ['pramworld.co.uk']
    start_urls = ['http://www.pramworld.co.uk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@id="navi"]//a/@href').extract()
        categories += hxs.select('//div[@class="category-view"]//div[@class="wrap"]/a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), meta=response.meta)

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

        next = hxs.select('//a[contains(@class, "i-next")]/@href').extract()
        if next:
            yield Request(urljoin_rfc(get_base_url(response), next[0]), meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(response=response, item=Product())

        loader.add_value('url', response.url)
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_xpath('sku', '//span[@itemprop="mpn"]/text()')
        loader.add_xpath('name', '//h1/span[@itemprop="name"]/text()')

        price = hxs.select('//form//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//form//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//meta[@property="og:price:amount"]/@content').extract()

        price = price[0] if price else 0
        loader.add_value('price', price)

        categories = hxs.select('//div[@class="breadcrumbs"]//li[not(@class="home")]/a/text()').extract()
        loader.add_value('category', categories)

        image_url = hxs.select('//meta[@property="og:image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        brand = hxs.select('//a[@class="brand-link"]/text()').re('View All (.*) Prod')
        loader.add_value('brand', brand)

        out_of_stock = hxs.select('//form//p[@class="availability out-of-stock"]')
        if out_of_stock or not loader.get_output_value('price'):
            loader.add_value('stock', 0)

        if loader.get_output_value('price')<50:
            loader.add_value('shipping_cost', 2.95)

        item = loader.load_item()

        product_swatches = hxs.select('//div[@class="product-swatches"]')
        options = hxs.select('//select[contains(@class, "bundle-option")]/option')
        if options and not product_swatches:
            for option in options:
                option_item = deepcopy(item)
                option_item['identifier'] += '-' + option.select('@value').extract()[0]
                option_item['name'] += ' ' + option.select('text()').extract()[0].split(' - ')[0]
                yield option_item
        else:
            yield item

