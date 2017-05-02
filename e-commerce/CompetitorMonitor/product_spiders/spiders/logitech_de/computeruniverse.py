import os
import csv

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class ComputeruniverseSpider(ProductCacheSpider):
    name = 'computeruniverse.net'
    allowed_domains = ['computeruniverse.net']
    start_urls = ('http://www.computeruniverse.net/manus/l10062/logitech.asp',)
    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0'
    concurrent_requests = 1
    download_delay = 5

    map_products_csv = os.path.join(HERE, 'logitech_map_products.csv')
    map_price_field = 'map'
    map_join_on = [('sku', 'mpn'), ('sku', 'ean13')]

    def start_requests(self):

        for url in self.start_urls:
            yield Request(url)

        with open(HERE + '/logitech_extra_products.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['ComputerUniverse'] != 'No Match':
                    product = Product()
                    request = Request(row['ComputerUniverse'], callback=self.parse_product, meta={'sku':row['sku'], 'brand':row['brand']})
                    yield self.fetch_product(request, product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        found = False
        for productxs in hxs.select('//div[contains(@class,"productsTableRow")]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//font[@class="priceItalicBig"]//text()').extract()))
            if productxs.select('.//*[contains(text(), "Bestellartikel")]'):
                product['stock'] = '0'
            else:
                product['stock'] = '1'

            request = Request(urljoin_rfc(get_base_url(response),
                                          productxs.select('.//h2/a/@href').extract()[0]),
                              callback=self.parse_product, meta=response.meta)
            found = True
            yield self.fetch_product(request, product)
        if not found:
            self.log("No products on %s" % response.body)

        for page in hxs.select('//ul[contains(@class,"pagination")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)
        url_parts = response.url.split('/')
        loader.add_xpath('identifier', url_parts[url_parts.index('products') + 1])

        sku = response.meta.get('sku', '')
        if sku:
            loader.add_value('sku', sku)
            price = hxs.select('//span[@itemprop="price"]/text()').extract()
            price = price[0] if price else '0'
            loader.add_value('price', extract_price_eu(price))
            if hxs.select('.//*[contains(text(), "Bestellartikel")]'):
                loader.add_value('stock', '0')
            else:
                loader.add_value('stock', '1')
            loader.add_value('brand', response.meta.get('brand', ''))
        else:
            loader.add_xpath('sku', 'substring-after(//*[contains(text(), "Hst-Nr.:")]/text(),"Hst-Nr.:")')
            if not loader.get_output_value('sku'):
                loader.add_xpath('sku', 'substring-after(//*[contains(text(), "Art-Nr.:")]/text(),"Art-Nr.:")')
            loader.add_value('brand', 'Logitech')

        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1//text()')

        try:
            loader.add_value('category', hxs.select('//span[@class="category"]/text()').extract()[-1])
        except IndexError:
            self.log("No category on %s" % response.body)

        img = hxs.select('//div[@id="mi_carousel"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('shipping_cost', '0')
        yield loader.load_item()
