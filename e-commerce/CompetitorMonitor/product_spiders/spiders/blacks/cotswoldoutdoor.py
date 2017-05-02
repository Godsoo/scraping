import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url


class CotswoldoutdoorSpider(BaseSpider):
    name = 'blacks-cotswoldoutdoor.com'
    allowed_domains = ['cotswoldoutdoor.com']
    start_urls = ('http://www.cotswoldoutdoor.com/?skipcountrycheck=1&changeCountry=',)

    def parse(self, response):
        yield Request('http://www.cotswoldoutdoor.com/mens/jackets/all-jackets', callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//a[contains(@href,"brand") and child::strong[@class="s"]]/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category, meta=response.meta)

        next_page = hxs.select('//li[@class="navi-right"]/a[child::div[@class="pager-button"]]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse_category, meta=response.meta)

        products = hxs.select('//p[@class="model"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), meta=response.meta, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        options = hxs.select('//select[@name="sku"]/@class').extract()
        for option in options:
            product_name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()
            colour = hxs.select('//ul[@id="picture-list"]/li/a[contains(@class, "'+option+'")]/img/@title').extract()[0]
            option_image =  hxs.select('//ul[@id="picture-list"]/li/a[contains(@class, "'+option+'")]/img/@large').extract()[0]
            product_name = product_name + ' - ' + colour

            category = hxs.select('//ul[@class="bread-crumb"]/li/a/xml-fragment/text()').extract()
            category = category[-2].strip() if category else ''

            image_url = option_image.replace('88x88', '370x370')

            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('url', response.url)

            product_loader.add_value('name', product_name)

            sku = hxs.select('//p[@class="product-code"]/span/text()').extract()[0] + '-' + option
            product_loader.add_value('sku', sku)
            product_loader.add_value('identifier', sku)

            options = hxs.select('//select[@name="sku"]/@class').extract()
            price = hxs.select('//div[@class="prices"]/p[contains(@class,"pc%s")]'
                               '//span[@itemprop="price"]/text()' % option).extract()
            price = price[0].strip() if price else '0.00'
            product_loader.add_value('price', price)

            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))

            product_loader.add_value('category', category)

            brand =  hxs.select('//div[@class="gallery-product-top-box"]/div/a/img[contains(@alt, "Logo for ")]/@alt').re(r'Logo for (.*)')
            brand = brand[0] if brand else ''
            product_loader.add_value('brand', brand)

            yield product_loader.load_item()
