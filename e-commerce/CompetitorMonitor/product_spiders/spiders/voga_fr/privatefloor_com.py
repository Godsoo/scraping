from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import re
import json


class PrivateFloorSpider(BaseSpider):
    name = 'voga_fr-privatefloor.com'
    allowed_domains = ['privatefloor.com']
    start_urls = []

    def start_requests(self):
        yield Request('https://secure.privatefloor.com', cookies={}, meta={'dont_merge_cookies': True})

    def parse(self, response):
        yield Request('https://secure.privatefloor.com/mfboutique/rechercheProduit.php',
                      cookies={}, meta={'dont_merge_cookies': True},
                      callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="product_container_boutique"]//div[@class="product_name"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url.replace('http', 'https').replace('://en.', '://secure.').replace('://www.', '://secure.')), callback=self.parse_product,
                          cookies={}, meta={'dont_merge_cookies': True})
        for url in hxs.select('//div[@class="paginationBoutique"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url.replace('http', 'https').replace('://en.', '://secure.').replace('://www.', '://secure.')), callback=self.parse_products,
                          cookies={}, meta={'dont_merge_cookies': True})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        brand = hxs.select("//p[@class='nomDesigner']/text()").extract()
        brand = brand[0].split('(')[0].strip() if brand else ''

        product_name = ''.join(hxs.select('//h1[@class="produit_title"]/text()').extract()).strip()
        category = hxs.select('//*[@id="retourvente"]/a/text()').extract()[1:]
        product_identifier = hxs.select('//*[@id="valorCat"]/text()').extract()[0]
        price = hxs.select('//*[@id="mfb_soldes_price"]/text()').extract()[0]
        price = extract_price_eu(price)
        match = re.search(r"var colors = JSON\.parse\('(.*?)'\);",
                          response.body_as_unicode(), re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if match:
            result = match.group(1)
        else:
            self.log('ERROR!!! NO COLOUR! {}'.format(response.url))
            return
        options = json.loads(result)
        if options:
            for option in options:
                loader = ProductLoader(item=Product(), selector=hxs)
                name = option['taille']
                if name != '':
                    name = product_name + ' - ' + name
                identifier = option['id']
                loader.add_value('identifier', product_identifier + '_' + str(identifier))
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('brand', brand)
                loader.add_value('price', price)
                loader.add_value('sku', product_identifier)
                if 'fotoN' in option:
                    loader.add_value('image_url', urljoin_rfc(get_base_url(response), option['fotoN']))
                loader.add_value('category', category)
                yield loader.load_item()
        else:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('identifier', product_identifier)
            loader.add_value('url', response.url)
            loader.add_value('name', product_name)
            loader.add_value('brand', brand)
            loader.add_value('price', price)
            loader.add_value('sku', product_identifier)
            loader.add_xpath('image_url', '//*[@id="zoom_picture"]/@src')
            loader.add_value('category', category)
            yield loader.load_item()
