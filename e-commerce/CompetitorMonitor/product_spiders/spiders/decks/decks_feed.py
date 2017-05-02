from scrapy.spider import BaseSpider
from scrapy.selector import XmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price


class DecksFeedSpider(BaseSpider):
    name = 'decks-feed'
    allowed_domains = ['decks.co.uk']
    start_urls = ('https://www.decks.co.uk/atom_products.xml',)

    def parse(self, response):
        xxs = XmlXPathSelector(response)
        base_url = get_base_url(response)
        xxs.register_namespace("f", "http://www.w3.org/2005/Atom")
        products = xxs.select('//f:entry')
        for product in products:
            product.register_namespace("g", "http://base.google.com/ns/1.0")
            product.register_namespace("p", "http://www.w3.org/2005/Atom")
            product_loader = ProductLoader(item=Product(), selector=product)
            name = product.select('./p:title/text()').extract()[0]
            if 'B-STOCK' in name.upper():
                continue
            product_loader.add_value('name', name)
            url = product.select('./p:link/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            image_url = product.select('./g:image_link/text()').extract()
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            category = product.select('./g:product_type/text()').extract()
            if category:
                product_loader.add_value('category', category[0])
            brand = product.select('./g:brand/text()').extract()
            if brand:
                product_loader.add_value('brand', brand[0])
            price = product.select('./g:sale_price/text()').extract()
            if price:
                product_loader.add_value('price', extract_price(price[0]))
            else:
                price = product.select('./g:price/text()').extract()
                product_loader.add_value('price', extract_price(price[0]))
            # sku = product.select('./g:gtin/text()').extract()
            # if sku:
            #     product_loader.add_value('sku', sku[0])
            identifier = product.select('./g:id/text()').extract()[0]
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('sku', identifier)
            shipping_cost = product.select('./g:shipping/g:price/text()').extract()
            if shipping_cost:
                product_loader.add_value('shipping_cost', extract_price(shipping_cost[0]))
            product = product_loader.load_item()
            yield product
