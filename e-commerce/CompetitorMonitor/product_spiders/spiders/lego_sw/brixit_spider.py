import re
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader
import scrapy
from scrapy.http import Request
import json


class BrixitSpider(scrapy.Spider):
    name = 'legosw-brixit.se'
    allowed_domains = ['uppolek.se']
    start_urls = ('http://uppolek.se/',)
    re_sku = re.compile('(\d\d\d\d\d?)')
    post_data = '[{"id": 78, "jsonrpc": "2.0", "method": "Article.list", "params": [' \
                '{"uid": true, "name": "sv", "price": true, "url": "sv", "images": true, "unit":' \
                'true, "articlegroup": true, "news": true, "choices": true, "isBuyable": true, ' \
                '"presentationOnly": true, "choiceSchema": true}, { "filters": {"/showInArticlegroups": {' \
                '"containsAny": [3317828, 3637801, 3637802, 2465283, 3376152, 1644486, 3662600, 1247096, 1738366,' \
                '1238304, 2648058, 1238301, 2234560, 1248520, 1238300, 2665549, 1238290, 1741148,' \
                '2371594, 1705184, 2234561, 1238293, 2753863, 1248501, 2159513, 1238303, 1345962,' \
                '2291353, 1248425, 3648386, 1238284, 2632725, 2468229, 2666452, 2669460, 1249325,' \
                '1238285, 1238299, 1237355, 1248527, 1741174, 1238331, 1238283, 2096623, 1237342,' \
                '1263441, 1392405, 1497638, 1249751, 1249753, 1249754, 1249755, 1249756, 1249757,' \
                '1249758, 1585097, 1740222, 1974367, 2056484, 2187691, 2289338, 2721079, 2455276,' \
                '2552954, 3310308, 3653794, 3805801, 1237344, 1236782, 1236783, 1236784, 1250717,' \
                '1236781]}}, "offset": {}, "limit": 200, "sort": "created", "descending": true}]}]'
    post_url = 'https://shop.textalk.se/backend/jsonrpc/v1/?language=sv&webshop=28328&auth='

    def parse(self, response):
        for url in response.css('ul.nav').xpath('.//a/@href[contains(., "/lego")]').extract():
            yield Request(response.urljoin(url), self.parse_category)
    
    def parse_category(self, response):
        for url in response.css('.product-grid a::attr(href)').extract():
            yield Request(response.urljoin(url), self.parse_product)
            
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        loader.add_css('identifier', 'input.qs-cart-pid::attr(value)')
        loader.add_xpath('identifier', '//script/text()', re='product_id=(.+)"')
        loader.add_value('url', response.url)
        loader.add_css('name', 'h1.product-description-header::text')
        loader.add_css('price', 'input.qs-cart-price::attr(value)')
        loader.add_value('price', 0)
        name = loader.get_output_value('name')
        sku = self.re_sku.findall(name)
        if sku:
            sku = max(sku, key=len)
            loader.add_value('sku', sku)
        loader.add_css('image_url', 'div.product-images ::attr(src)')
        stock = response.xpath('//link[@itemprop="availability"]/@href').extract_first()
        if not stock or 'instock' not in stock.lower():
            loader.add_value('stock', 0)       
        yield loader.load_item()
        
    def parse_products(self, response):
        data = json.loads(response.body)
        if data[0]['result']:
            for product in data[0]['result']:
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', product['name']['sv'])
                if product['images']:
                    product_loader.add_value('image_url', product['images'][0])
                product_loader.add_value('url', product['url']['sv'])
                product_loader.add_value('identifier', product['uid'])
                sku = product['name']['sv']
                sku = self.re_sku.findall(sku)
                product_loader.add_value('sku', sku)
                product_loader.add_value('price', product['price']['current']['SEK'])
                if not product['isBuyable']:
                    product_loader.add_value('stock', 0)
                product = product_loader.load_item()
                yield product
            offset = response.meta['offset'] + 200
            data = self.post_data.replace('{}', str(offset))
            yield scrapy.Request(self.post_url, method='POST', body=data,
                                 callback=self.parse_products, meta={'offset': offset},
                                 dont_filter=True)
