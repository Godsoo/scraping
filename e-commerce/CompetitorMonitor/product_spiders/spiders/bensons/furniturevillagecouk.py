from scrapy import Spider, Request
from scrapy.utils.url import (
    url_query_parameter,
    add_or_replace_parameter,
)
from product_spiders.items import Product, ProductLoader
from product_spiders.lib.schema import SpiderSchema
from decimal import Decimal
from scrapy.item import Item, Field


class Meta(Item):
    net_price = Field()


class Furniturevillageco(Spider):
    name = 'bensons-furniturevillage.co.uk'
    allowed_domains = ['furniturevillage.co.uk']
    start_urls = ['http://www.furniturevillage.co.uk/']

    def __init__(self, *args, **kwargs):
        super(Furniturevillageco, self).__init__(*args, **kwargs)

        self.items = []

    def parse(self, response):
        categories = {}
        for c in response.xpath('//*[@id="mainMenu"]//div[contains(@class, "level-3")]//a'):
            url = c.xpath('@href').extract()[0]
            text = c.xpath('text()').extract()[0].strip()
            if ('/brands/' not in url) and (text not in categories):
                categories[text] = url

        for c_desc, c_url in categories.items():
            yield Request(
                response.urljoin(c_url),
                callback=self.parse_category,
                meta={'category': c_desc}
            )


    def parse_category(self, response):
        items = set(response.xpath('//li[@data-productid]//a[contains(@class, "name-link")]/@href').extract())
        for url in items:
            yield Request(
                response.urljoin(url),
                callback=self.parse_product,
                meta={'category': response.meta['category']}
            )

        if items and len(items) >= 12:
            # Try next page
            start_index = int(url_query_parameter(response.url, 'start', '0')) + 12
            url = add_or_replace_parameter(response.url, 'sz', '12')
            url = add_or_replace_parameter(url, 'start', str(start_index))
            yield Request(
                url,
                callback=self.parse_category,
                meta={'category': response.meta['category']}
            )

    def parse_product(self, response):
        # Normal options
        options = response.xpath('//select[@class="variation-select"]/option[not(@selected)]')
        options = zip(map(unicode.strip, options.xpath('text()').extract()), options.xpath('@value').extract())
        for desc, url in options:
            yield Request(url,
                          meta={'category': response.meta.get('category'),
                                'option': desc},
                          callback=self.parse_product)

        # Variations popup
        variations_url = response.xpath('//div[@class="variations"]//a/@data-href').extract()
        if variations_url:
            url = response.urljoin(variations_url[0])
            yield Request(url, callback=self.parse_variations, meta=response.meta)

        schema = SpiderSchema(response)
        product = schema.get_product()

        name = product['name']

        # Normal option selected
        current_option = map(
            unicode.strip,
            response.xpath('//select[@class="variation-select"]/option[@selected]/text()')
            .extract())
        if current_option:
            name += ' - ' + current_option[0]

        # Variation selected
        currently_selected = response.xpath('//div[@class="variations"]'
            '//div[contains(@class, "variation-attribute-selected-value")]/text()')\
            .extract()
        if currently_selected:
            current_option = currently_selected[-1].strip()
            name += ' - ' + current_option[0]

        identifier = product['productID']
        price = product['offers']['properties']['price']
        image_url = product['image']
        category = response.meta.get('category')

        if not category:
            category = [c['properties']['name'] \
                for c in schema.data['items'][0]['properties']\
                        ['breadcrumb']['properties']['itemListElement'][1:-1]]
        else:
            category = category.split(',')

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('image_url', image_url)
        loader.add_value('price', price)
        for cat in category:
            loader.add_value('category', cat)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        if not identifier in self.items:
            self.items.append(identifier)
            yield self.preprocess_product(loader.load_item())

    def parse_variations(self, response):
        variants_urls = response.xpath('//div[contains(@class, '
            '"product-popup-variations")]//input[not(@checked)]/@value')\
            .extract()
        for url in variants_urls:
            yield Request(response.urljoin(url),
                          callback=self.parse_product,
                          meta=response.meta)

    def preprocess_product(self, item):
        price = Decimal(item['price'])
        net_price = price / Decimal('1.2')

        meta_ = Meta()
        meta_['net_price'] = str(net_price)
        item['metadata'] = meta_

        return item
