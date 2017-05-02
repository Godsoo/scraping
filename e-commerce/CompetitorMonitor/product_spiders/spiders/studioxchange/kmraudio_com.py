from urlparse import urljoin
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider


class KmrAudioSpider(BaseSpider):
    name = 'www.kmraudio.com'
    allowed_domains = ['www.kmraudio.com']
    start_urls = ['https://www.kmraudio.com/products.php',
                  'https://www.kmraudio.com/shop.php',
                  'https://www.kmraudio.com/brands.php']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//ul[contains(@class, "brandLogos")]//a/@href|//ul[@id="nav"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin(base_url, url))

        products = hxs.select('//div[@class="category-products"]//h2[@class="product-name"]/a/@href').extract()
        if products:
            try:
                category = hxs.select('//div[@class="breadcrumbs"]//li/*/text()').extract()[-1].strip()
            except IndexError:
                category = ''

            for url in products:
                yield Request(urljoin(base_url, url),
                              callback=self.parse_product,
                              meta={'category': category})

        # parse next pages
        pages = hxs.select('//div[@class="pages"]//a/@href').extract()
        for url in pages:
            yield Request(urljoin(base_url, url))

    def parse_product(self, response):
        """
        No shipping cost found
        """
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brand = hxs.select('//table[@id="product-attribute-specs-table"]//th[@class="label" and contains(text(), "Manufacturer")]/following-sibling::*/text()').extract()[0]

        loader = ProductLoader(response=response, item=Product())

        #price = hxs.select('//*[@id="price-including-tax-6649"]//text()').re(r'[\d.,]+')
        price = None
        if not price:
            price = hxs.select('//div[@class="productBox"]//div[@class="price-box"]/p[@class="price-to"]/span[@class="price-including-tax"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="productBox"]//div[@class="price-box"]//span[@class="price-including-tax"]/span[@class="price"]/text()').extract()
        loader.add_value('price', price)
        if not loader.get_output_value('price'):
            loader.add_value('price', '0.0')
            loader.add_value('stock', '0')

        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_value('url', urljoin(base_url, response.url))
        loader.add_value('brand', brand)
        loader.add_xpath('name', '//div[@class="product-name"]/h1/text()')

        image_url = hxs.select('//img[@id="zoom"]/@src').extract()
        if not image_url:
            image_url = hxs.select('//a[@id="ma-zoom1"]/@href').extract()
        loader.add_value('image_url', image_url)
        loader.add_value('category', response.meta.get('category', ''))
        yield loader.load_item()
