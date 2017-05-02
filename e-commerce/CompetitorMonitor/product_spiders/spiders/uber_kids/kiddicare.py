"""
Uber Kids account
Kiddicare spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4829
"""

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import json
import itertools

class Kiddicare(CrawlSpider):
    name = 'uberkids-kiddicare'
    allowed_domains = ['kiddicare.com']
    start_urls = ['http://www.kiddicare.com']

    categories = LinkExtractor(allow='/c/')
    pages = LinkExtractor(allow='/c/', restrict_css='.pagination')
    products = LinkExtractor(allow='/p/')

    identifiers = set()

    rules = (
        Rule(categories, callback='parse_category'),
        )

    instock = (
        'nextday-selectday',
        '48hours',
        '48hours-selectday',
        '2-3days',
        '3-5days',
        '1week',
        '1-2weeks')
    outofstock = (
        '2-3weeks',
        '3-4weeks',
        '4-6weeks',
        '6-8weeks',
        '8-12weeks',
        '10-14weeks')

    def parse_category(self, response):
        category = response.meta.get('link_text') or response.meta.get('category')
        if not category or '#menu' in category:
            return
        category = category.strip()
        if not category:
            return
        meta = {'category': category}
        for page in self.pages.extract_links(response):
            yield Request(page.url, self.parse_category, meta=meta)
        for product in self.products.extract_links(response):
            yield Request(product.url, self.parse_product, meta=meta)

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('category', response.meta['category'])
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        option_name = response.css('.label-select-container').xpath('.//option[@selected]/text()').extract()
        loader.add_value('name', option_name)
        item_identifier = response.xpath('//input[@id="item_details_item_id"]/@value').extract_first()
        if not item_identifier:
            self.logger.warning('No identifier on %s' %response.url)
        identifier = item_identifier + '-' + response.xpath('//input[@id="item_details_product_id"]/@value').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        sku = []
        sku.append(response.css('.order-code').xpath('text()').extract_first().strip())
        sku.extend(response.css('.order-code span::text').extract())
        loader.add_value('sku', ' '.join(sku))
        loader.add_xpath('image_url', '//img[@id="imageMain"]/@src')
        loader.add_css('brand', '.sku_kc_brand_id_ ::text')
        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', '2.99')
        stock = response.xpath('//meta[@itemprop="availability"]/@content').extract_first()
        stock = stock.replace(' ', '').lower()
        if stock not in self.instock:
            loader.add_value('stock', 0)
            if stock not in self.outofstock:
                self.logger.warning('Undefined stock status for %s' %response.url)
        item = loader.load_item()
        if item['identifier'] not in self.identifiers:
            self.identifiers.add(item['identifier'])
            yield item

        attributes = []
        options = []
        for attribute in response.css('.label-select-container select'):
            attribute_name = attribute.xpath('@id').extract_first()
            attribute_name = attribute_name.replace('_%s' %item_identifier, '')
            attributes.append(attribute_name)
            options.append([])
            for value in attribute.xpath('option/@value').extract():
                options[-1].append(value)
        for variant in itertools.product(*options):
            url = 'http://www.kiddicare.com/ajax.get_exact_product.php?instart_disable_injection=true&item_id=%s' %item_identifier
            for n, option in enumerate(variant):
                url += '&attributes[%s]=%s' %(attributes[n], option)
            url = url.replace('+', '%2B')
            meta = response.meta
            meta['sku'] = sku
            meta['attributes'] = attributes
            yield Request(url, self.parse_option, meta=meta)

    def parse_option(self, response):
        data = json.loads(response.body)['data']
        if not data or not data.get('item_id'):
            self.logger.warning('Not enough data on %s' %response.url)
            return
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', data['item_id'] + '-' + data['id'])
        loader.add_value('url', response.request.headers['Referer'])
        loader.add_value('name', data['product_name'])
        for attribute in response.meta['attributes']:
            if data.get(attribute) and data[attribute] not in data['product_name']:
                loader.add_value('name', data[attribute])
        loader.add_value('price', data['ourprice'])
        old_sku = response.meta['sku']
        sku = ' '.join((old_sku[0], data['id']))
        if len(old_sku) == 3:
            sku += ' ' + old_sku[2]
        loader.add_value('sku', sku)
        loader.add_value('category', response.meta['category'])
        base_image_url = 'https://images.static.worldstores.co/images/products/WP/'
        images = json.loads(data['image_names'])
        loader.add_value('image_url', base_image_url + images[0]['image_name'])
        brand = data.get('kc_brand') or data.get('brand')
        loader.add_value('brand', brand)
        if data['ourprice'] < 50:
            loader.add_value('shipping_cost', '2.99')
        stock = data['availability_message'].replace(' ', '').lower()
        if stock not in self.instock:
            loader.add_value('stock', 0)
            if stock not in self.outofstock:
                self.logger.warning('Undefined stock status for %s' %response.url)
        item = loader.load_item()
        if item['identifier'] not in self.identifiers:
            self.identifiers.add(item['identifier'])
            yield item
