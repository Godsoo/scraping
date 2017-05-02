from decimal import Decimal
import re
import demjson
from scrapy.selector import HtmlXPathSelector
from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from fragrance_direct_items import FragranceDirectMeta


class CBBootsSpider(BaseSpider):
    name = 'fragrancedirect-boots.com'
    allowed_domains = ['boots.com']
    start_urls = ['http://www.boots.com/webapp/wcs/stores/servlet/TopCategoriesDisplay?storeId=10052&langId=-1&isRedirect=Y&geoCode=GB']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        # Beauty
        for url in hxs.select('//*[@id="ia_supernav"]/ul/li[2]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_list)
        # Fragrance
        for url in hxs.select('//*[@id="ia_supernav"]/ul/li[3]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_list)
        # Toiletries
        for url in hxs.select('//*[@id="ia_supernav"]/ul/li[5]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_list)
        # Men
        for url in hxs.select('//*[@id="ia_supernav"]/ul/li[6]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_list)
        # Gift
        for url in hxs.select('//*[@id="ia_supernav"]/ul/li[11]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="guidedNavigationInner"]//div[@class="facet openMenuDefault"]//li[not(@class)]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_list)
        for url in hxs.select('//div[contains(@class,"product_item")]//h5/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)
        for url in hxs.select('//li[@class="paginationTop"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        options = None
        js_line = ''
        for l in response.body.split('\n'):
            if 'variants:' in l:
                js_line = l
                break

        if js_line:
            options = demjson.decode(re.search(r'variants:(.*};)?', js_line).groups()[0][:-2].strip())

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_identifier = hxs.select('//input[@id="productId" or @name="productId"]/@value').extract()[0]
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('url', response.url)
        name = hxs.select('//span[@itemprop="name"]/text()').extract()[0]
        product_loader.add_value('name', name)
        category = hxs.select('//*[@id="breadcrumb"]//a/text()').extract()[1:-1]
        product_loader.add_value('category', category)
        product_loader.add_xpath('sku', '//span[@class="pd_productVariant"]/text()')
        img = hxs.select('//meta[@property="og:image"]/@content').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop()))
        price = hxs.select('//p[@class="productOfferPrice"]/text()').extract()[0]
        price = extract_price(price)
        product_loader.add_value('price', price)
        brand = hxs.select('//*[@id="brandHeader"]/a/@href').extract()
        if brand:
            brand = brand[0].replace('/en/', '')[:-1]
            product_loader.add_value('brand', brand)
        stock = ''.join(hxs.select('//div[@class="cvos-availbility-panel"]/p/text()').extract())
        if 'Item is currently out of stock online' in stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        metadata = FragranceDirectMeta()
        prom = ''.join(hxs.select('//div[@class="productSavings"]//text()').extract())
        metadata['promotion'] = prom + ' ' + ''.join(hxs.select('//div[@class="primaryItemDeal"]//p/text()').extract())
        if product['price']:
            metadata['price_exc_vat'] = Decimal(product['price']) / Decimal('1.2')
        product['metadata'] = metadata

        yield product

        if options:
            for k, val in options.items():
                option_name = k.replace('_', ' ')
                option_product = Product(product)
                option_product['name'] = product['name'] + ' ' + option_name
                option_product['sku'] = val['productCode']
                option_product['identifier'] = val['variantId']
                option_product['price'] = extract_price(val['nowPrice'])
                if option_product.get('price'):
                    option_product['metadata']['price_exc_vat'] = Decimal(option_product['price']) / Decimal('1.2')

                yield option_product
