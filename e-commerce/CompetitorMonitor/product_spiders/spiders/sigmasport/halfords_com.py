"""
Account: SigmaSport
Name: sigmasport-halfords.com
"""


import json
import re
from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from scrapy.utils.url import add_or_replace_parameter

from sigmasportitems import SigmaSportMeta, extract_exc_vat_price


class HalfordsComSpider(Spider):
    name = 'sigmasport-halfords.com'
    allowed_domains = ['halfords.com', 'competitormonitor.com']
    start_urls = ('http://www.halfords.com/cycling',)

    def __init__(self, *args, **kwargs):
        super(HalfordsComSpider, self).__init__(*args, **kwargs)

        self._identifiers_viewed = set()

    def _start_requests(self):
        return [Request('http://www.halfords.com/cycling/bike-maintenance/bike-lube/park-tool-asc1-anti-seize-compound', callback=self.parse_product)]

    def parse(self, response):
        for url in response.xpath('//ul[@class="sideNav-ul"]/li/a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_category_or_product_list)


    def parse_category_or_product_list(self, response):
        try:
            categories_urls = response.xpath('//span[@class="categoryTitle"]/a/@href').extract()
        except:
            retry = response.meta.get('retry', 0)
            if retry < 10:
                retry = retry + 1
                meta = response.meta.copy()
                meta['retry'] = retry
                self.log('>>> ERROR: Retrying No. %s => %s' % (str(retry), response.url))
                yield Request(response.url,
                              meta=meta,
                              dont_filter=True,
                              callback=self.parse_category_or_product_list)
                return
            else:
                categories_urls = []
        if categories_urls:
            for url in categories_urls:
                yield Request(response.urljoin(url), callback=self.parse_category_or_product_list)
        else:

            # pagination
            next_page = response.xpath('//a[@class="pageLink next"]/@href').extract()
            if next_page:
                yield Request(response.urljoin(next_page[0]), callback=self.parse_category_or_product_list)

            for product_url in response.xpath('//*[@id="product-listing"]//a[@class="productModuleTitleLink"]/@href').extract():
                yield Request(response.urljoin(product_url), self.parse_product)


    def parse_product(self, response):

        try:
            category = response.xpath('//nav[@id="breadcrumb"]//ul/li[@class="penultimateStep"]/a/text()').extract()[0].strip()
        except IndexError:
            category = ''
        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        if image_url:
            image_url = image_url[0].replace('merchzone', 'main')
        brand = response.xpath('//div[@class="hproduct"]/span[@class="brand"]/text()').extract()
        price = response.xpath('//div[@id="priceAndLogo" or @id="priceAndRating"]/h2/text()').re(r'[\d,.]+')

        options = re.findall('multiVariantArray:(.*),', response.body)
        try:
            variants = json.loads(options[0].strip())
        except:
            options = ''
        if options and response.xpath('//div[@class="productOptions"]//div[contains(@id, "itemVariantSelectionWidget")]'):
            parameters = {
                'action': 'getProductItemDetails',
                'langId': '-1',
                'storeId': '10001'
                }
            msg = {
                'productId': response.xpath('//input[@name="productId"]/@value').extract()[0].encode(),
                'catalogId': response.xpath('//input[@name="catalogId"]/@value').extract()[0].encode(),
                'categoryId': response.xpath('//input[@name="categoryId"]/@value').extract()[0].encode()
            }
            option_url = 'http://www.halfords.com/webapp/wcs/stores/servlet/GetProductItemDetails'
            for variant in variants:
                msg['catEntryId'] = variant['itemId']
                parameters['msg'] = msg
                url = option_url
                for par in parameters:
                    url = add_or_replace_parameter(url, par, parameters[par])
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', category)
                product_loader.add_value('brand', brand)
                product_loader.add_value('image_url', image_url)
                product = product_loader.load_item()
                yield Request(url, meta={'item':Product(product)}, callback=self.parse_options)
            return

        identifier = response.xpath('//input[@name="productId"]/@value').extract()
        if not identifier:
            self.log('No identifier found for %s' %response.url)
            return
        identifier = identifier.pop()
        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('sku', identifier)
        product_loader.add_xpath('name', '//h1[@class="productDisplayTitle"]/text()')
        price = response.xpath('//div[@class="productDisplayPricing"]'
                           '//div[@class="pricewrapper"]/div[@class="total"]'
                           '/span[@class="totalPrice"]/text()').extract()

        if not price:
            price = re.findall("price:\s?\'&pound;(.+?)\'", response.body)
            if not price:
                self.log('WARNING: No price can be found, ignoring product %s' %response.url)
                return
        price = extract_price(price[0])
        if price:
            shipping = 2.99 if price < 30 else ''
            product_loader.add_value('price', price)
            product_loader.add_value('shipping_cost', shipping)
            product_loader.add_value('url', response.url)
            product_loader.add_value('category', category)
            product_loader.add_value('image_url', image_url)
            product_loader.add_value('brand', brand)
            if response.xpath('//div[@id="productBuyable"][@class="hidden"]'):
                product_loader.add_value('stock', 0)
            product = product_loader.load_item()
            metadata = SigmaSportMeta()
            metadata['price_exc_vat'] = extract_exc_vat_price(product)
            product['metadata'] = metadata
            if product['identifier'] not in self._identifiers_viewed:
                #if self.simple_run and (product['identifier'] not in self.matched_identifiers):
                    #return
                self._identifiers_viewed.add(product['identifier'])
                yield product

    def parse_options(self, response):
        data = json.loads(response.body_as_unicode())['productItemDetails']
        product_loader = ProductLoader(item=Product(response.meta['item']), response=response)
        product_loader.add_value('name', data['name'])
        product_loader.add_value('identifier', data['itemCode'])
        product_loader.add_value('sku', data['itemCode'])
        product_loader.add_value('price', data['nowPriceRaw'])
        if not data['inStock']:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        if product['price'] < 30:
            product['shipping_cost'] = 2.99
        metadata = SigmaSportMeta()
        metadata['price_exc_vat'] = extract_exc_vat_price(product)
        product['metadata'] = metadata
        if product['identifier'] not in self._identifiers_viewed:
            if self.simple_run and (product['identifier'] not in self.matched_identifiers):
                return
            self._identifiers_viewed.add(product['identifier'])
            yield product

    def parse_product_data(self, response):
        s = response.body
        try:
            content = unicode(s, 'utf-8', errors='replace')
        except (LookupError, TypeError):
            content = unicode(s, errors='replace')
        try:
            data = json.loads(content)
        except ValueError:
            meta = response.meta
            retry = meta.get('retry', 1)
            retry += 1
            if retry < 10:
                meta['retry'] = retry
                self.log('WARNING - Retry #{} {}'.format(retry, response.meta.get('url')))
                yield Request(response.url,
                              meta=meta,
                              callback=self.parse_product_data,
                              dont_filter=True)
            else:
                self.log('ERROR - Maximum retry count reached! {} {}'.format(response.meta.get('url'), response.body))
                yield []
        else:
            item = data.get('productItemDetails')
            if item:
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', item.get('name'))
                price = extract_price(item.get('nowPriceRaw'))
                if price:
                    shipping = 2.99 if price < 30 else ''
                    product_loader.add_value('price', price)
                    product_loader.add_value('shipping_cost', shipping)
                    product_loader.add_value('category', response.meta.get('category'))
                    product_loader.add_value('url', response.meta.get('url'))
                    # product_loader.add_value('image_url', image_url)
                    product_loader.add_value('brand', response.meta.get('brand'))
                    product_loader.add_value('sku', item.get('itemCode'))
                    product_loader.add_value('identifier', item.get('itemCode'))
                    product = product_loader.load_item()
                    metadata = SigmaSportMeta()
                    metadata['price_exc_vat'] = extract_exc_vat_price(product)
                    product['metadata'] = metadata
                    if product['identifier'] not in self._identifiers_viewed:
                        if self.simple_run and (product['identifier'] not in self.matched_identifiers):
                            return
                        self._identifiers_viewed.add(product['identifier'])
                        yield product


    def closing_parse_simple(self, response):
        for obj in super(HalfordsComSpider, self).closing_parse_simple(response):
            if isinstance(obj, Product):
                if obj['identifier'] not in self._identifiers_viewed:
                    self._identifiers_viewed.add(obj['identifier'])
                    yield obj
            else:
                yield obj
