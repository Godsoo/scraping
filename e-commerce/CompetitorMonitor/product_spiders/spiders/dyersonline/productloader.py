import HTMLParser

from scrapy.contrib.loader.processor import MapCompose

from product_spiders.items import ProductLoader, Product
from product_spiders.utils import extract_price2uk

def remove_entities(s):
    parser = HTMLParser.HTMLParser()
    res = s.strip()
    return parser.unescape(res)

class WindowsCleaningProductLoader(ProductLoader):
    name_in = MapCompose(unicode, remove_entities, unicode.strip)
    price_in = MapCompose(extract_price2uk)

def load_product(product, response):
    p = Product()
    loader = WindowsCleaningProductLoader(item=p, response=response)
    loader.add_value('url', product['url'])
    loader.add_value('name', product['description'])
    loader.add_value('price', product['price'])
    loader.add_value('sku', product.get('sku', ''))
    loader.add_value('identifier', product.get('identifier', ''))
    loader.add_value('category', product.get('category', ''))
    loader.add_value('image_url', product.get('image_url', ''))
    loader.add_value('brand', product.get('brand', ''))
    loader.add_value('shipping_cost', product.get('shipping_cost', ''))
    loader.add_value('stock', product.get('stock', None))

    return loader.load_item()
