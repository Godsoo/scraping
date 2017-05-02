import os
import json

from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
HERE = os.path.abspath(os.path.dirname(__file__))


class HarveyNormanSpider(SitemapSpider):
    name = 'harveynorman.com.au'
    allowed_domains = ['harveynorman.com.au']
    sitemap_urls = ['http://www.harveynorman.com.au/sitemap.xml']
    sitemap_rules = [
        ('.html', 'parse_product'),
    ]

    def __init__(self, *args, **kwargs):
        super(HarveyNormanSpider, self).__init__()
        self.idents = set()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        products_json = hxs.select('//script/text()').re(r'Product.Config\((\{.*\})\)')

        options = False

        brand = hxs.select('//img[@class="brand-logo"]/@title').extract()
        if not brand:
            brand = hxs.select('//tr[th/text()="Brand"]/td/text()').extract()
        brand = brand[0] if brand else ''

        sku = hxs.select('//small[contains(@class, "product-id")][1]/text()').extract()
        if not sku:
            sku = hxs.select('//script/text()').re('PAGE_INFO\["sku"\].+"(.+)"')
        sku = sku[0] if sku else ''

        image_url = hxs.select('//div[@class="item active"]//img/@src').extract()
        image_url = image_url[0] if image_url else ''

        if products_json:
            try:
                products = json.loads(products_json[0])
            except:
                pass
            else:
                if len(products['childProducts']) > 0:
                    options = True
                    for k, product in products['childProducts'].items():
                        loader = ProductLoader(item=Product(), response=response)
                        loader.add_value('name', product['productName'])
                        loader.add_value('url', response.url)
                        loader.add_value('sku', product['productSku'])
                        loader.add_value('identifier', product['product_identifier'])
                        loader.add_xpath('category', '//div[@class="label" and text()="Product Type"]/following-sibling::div/text()')
                        loader.add_value('brand', brand)
                        loader.add_value('image_url', image_url)
                        loader.add_value('price', product['finalPrice'])
                        item = loader.load_item()
                        if item['identifier'] not in self.idents:
                            self.idents.add(item['identifier'])
                            yield item

        if not options:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_xpath('name', '//*[@id="content"]//span[@class="product-name"]/text()')
            loader.add_value('url', response.url)
            loader.add_value('sku', sku)
            loader.add_xpath('identifier', '//form/@action', re=r'/product/(\d+)/')
            loader.add_xpath('identifier', '//input[@name="product_id"]/@value')
            loader.add_xpath('category', '//div[@class="label" and text()="Product Type"]/following-sibling::div/text()')
            loader.add_value('brand', brand)
            loader.add_value('image_url', image_url)

            price = hxs.select('//*[@id="product-view-price"]/div/div/span/span/text()').re(r'[\d.,]+')
            if not price:
                price = hxs.select('//div["product-view-price"]/@data-price').re(r'[\d.,]+')
            if not price:
                price = hxs.select('//*[@id="product-view-price"]/div/div/div/span/span[@class="price"]/text()').re(r'[\d.,]+')
            if price:
                if hxs.select('//div["product-view-price"]//div[@class="in-store-only"]'):
                    loader.add_value('price', '0.0')
                else:
                    loader.add_value('price', price[0])
                item = loader.load_item()
                if item['identifier'] not in self.idents:
                    self.idents.add(item['identifier'])
                    yield item
