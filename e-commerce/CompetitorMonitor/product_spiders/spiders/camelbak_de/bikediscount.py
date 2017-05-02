"""
Account: CamelBak DE
Name: camelbak_de-bike-discount.de
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4619
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
"""


from scrapy import Spider, Request
from scrapy.http import HtmlResponse
from scrapy.utils.url import url_query_parameter, add_or_replace_parameter
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)
from product_spiders.utils import extract_price_eu, extract_price
from urllib import urlencode
import demjson
import re
import HTMLParser


class CamelBakBikeDiscount(Spider):
    name = 'camelbak_de-bike-discount.de'
    allowed_domains = ['bike-discount.de']

    # Set the country
    start_urls = ['http://www.bike-discount.de/en']
    json_next_url = 'http://www.bike-discount.de/json.php?service=getProductsContent&order_by=ranking'

    def __init__(self, *args, **kwargs):
        super(CamelBakBikeDiscount, self).__init__(*args, **kwargs)
        self.identifiers = []

    def parse(self, response):
        meta = response.meta
        if not meta.get('set_currency', False):
            meta['set_currency'] = True
            yield Request('http://www.bike-discount.de/en?currency=1&delivery_country=48', meta=meta)
        else:
            url = 'http://www.bike-discount.de/de/camelbak'
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        if not isinstance(response, HtmlResponse):
            try:
                data = demjson.decode(response.body)
                response = HtmlResponse(response.url,
                                        body=data['data'],
                                        encoding='utf-8',
                                        request=response.request)
            except:
                self.log('No valid json found in %s' % response.url)
                return

        products = response.xpath(u'//a[@itemprop="url"]/@href').extract()

        for url in products:
            url = response.urljoin(url)
            yield Request(url, callback=self.parse_product)

        if products:
            pages = response.xpath('//ul[contains(@class, "uk-pagination")]//a/@href').extract()
            for page in pages:
                yield Request(response.urljoin(page), callback=self.parse_product_list)

    def parse_product(self, response):
        try:
            brand_name = response.xpath('//span[@class="manufacturer"]/text()').extract()[0]
            name = response.xpath('//div[@id="product-box"]//div[@class="title"]/text()').extract()[0].strip()
        except:
            self.log('No brand or name found: %s' % response.url)
            return

        if response.xpath('//div[@class="no-valid-variants" and contains(text(), "this item is currently not available")]'):
            return

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('url', response.url)
        product_loader.add_value('name', brand_name + ' ' + name)
        sku = response.xpath('////div[@class="additional-product-no"]/@data-xencoded').extract()
        if sku:
            sku = sku[0]
            h = HTMLParser.HTMLParser()
            key, data = sku.split(':', 1)
            key = int(key)
            data = h.unescape(data)
            # XOR decoding
            data = [ord(c) ^ key for c in data]
            data = ''.join([chr(c) for c in data])
            sku = re.search('Manufacturer Item no\. (.*)', data)
            if sku:
                sku = sku.group(1)
                # 'Hersteller Artikelnr: 20050/20051'
                product_loader.add_value('sku', sku)
        # product_loader.add_xpath('sku', u'//div[@class="additional-product-no" and contains(text(), "Manufacturer Item no.")]', re=r'Manufacturer Item no\. (.*)')
        identifier = response.xpath('//input[@name="vw_id"]/@value').extract()[0]
        product_loader.add_value('identifier', identifier)


        price = response.xpath('//div[@class="current-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = response.xpath('//table[@class="product-price"]//tr[@class="price"]/td/text()').extract()
        if price:
            price = price[0]
            product_loader.add_value('price', extract_price_eu(price))
        else:
            self.log('No product price found: %s' % response.url)
            return

        category = response.css('.uk-breadcrumb a::text').extract()[-1]

        product_loader.add_value('category', category)

        product_loader.add_value('brand', brand_name.strip())

        try:
            image_url = response.urljoin(response.xpath('//img[@itemprop="image"]/@src').extract()[0])
            product_loader.add_value('image_url', image_url)
        except:
            pass
        product = product_loader.load_item()

        rrp = extract_price_eu(''.join(response.xpath('//span[@class="retail-value"]/text()').extract()))
        rrp = str(rrp) if rrp>extract_price_eu(price) else ''

        options = response.xpath('//div[contains(@id,"artikel_element_prices")]')
        if options:
            for opt in options:
                p = Product(product)
                optname =  opt.xpath('.//meta[@itemprop="name"]/@content').extract()[0]
                p['name'] = optname
                p['price'] = extract_price(opt.xpath('.//meta[@itemprop="price"]/@content').extract()[0])
                p['identifier'] = p['identifier'] + '-' + opt.xpath('@id').re('artikel_element_prices(.*)')[0]
                if p['identifier'] not in self.identifiers:
                    self.identifiers.append(p['identifier'])
                    yield p
        else:
            if product['identifier'] not in self.identifiers:
                self.identifiers.append(product['identifier'])
                yield product
