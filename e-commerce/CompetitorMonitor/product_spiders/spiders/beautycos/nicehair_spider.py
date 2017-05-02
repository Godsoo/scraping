
from scrapy.spider import BaseSpider
from scrapy.selector import XmlXPathSelector

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
from product_spiders.utils import extract_price_eu


class NiceHairSpider(BaseSpider):
    name = 'beautycos-nicehair.dk'
    allowed_domains = ['nicehair.dk']
    start_urls = ('http://admin.nicehair.dk/feed/competitor_nicehair_1.xml',)

    def parse(self, response):
        xxs = XmlXPathSelector(response)

        for product in xxs.select('//product'):
            category = product.select('./Category/text()').extract()
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('identifier', './product-id/text()')
            loader.add_xpath('sku', './product-id/text()')
            loader.add_xpath('url', './product-url/text()')
            loader.add_xpath('name', './product-name/text()')
            loader.add_xpath('brand', './brand/text()')
            loader.add_value('price', extract_price_eu(' '.join(product.select('./price/text()').extract())))
            if category:
                loader.add_value('category', category[0].split('/')[-1].strip())
            loader.add_xpath('image_url', './image-url/text()')
            loader.add_xpath('stock', './stock/text()')
            if loader.get_output_value('price') > 499:
                loader.add_value('shipping_cost', '0')
            else:
                loader.add_value('shipping_cost', '25')
            yield loader.load_item()
