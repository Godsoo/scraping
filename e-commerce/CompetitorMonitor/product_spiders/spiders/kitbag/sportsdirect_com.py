# -*- coding: utf-8 -*-


"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4933

The spider crawls categories "Football shirts", http://www.sportsdirect.com/football/footballs and http://www.sportsdirect.com/mens/mens-football-boots
Collects all options.
"""


import json
from decimal import Decimal
from scrapy import Spider, Request
from scrapy.utils.url import add_or_replace_parameter
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


personalise_url = 'http://www.sportsdirect.com/ProductPersonalisation?sv={}'


SIZE_MAP = {
    'Extra Sml': 'XS',
    'Small': 'S',
    'Medium': 'M',
    'Large': 'L',
    'Extra Lge': 'XL',
    'XX Large': '2XL',
    'XXX Large': '3XL',
}


class SportsdirectSpider(Spider):
    name = 'kitbag-sportsdirect.com'
    allowed_domains = ['sportsdirect.com']
    start_urls = ('http://www.sportsdirect.com/football-shirts',
                  'http://www.sportsdirect.com/football/footballs',
                  'http://www.sportsdirect.com/mens/mens-football-boots'
                  )

    def __init__(self, *args, **kwargs):
        self.processed_next_categories = False
        dispatcher.connect(self.process_next_category, signals.spider_idle)
        super(SportsdirectSpider, self).__init__(*args, **kwargs)
        self.errors = []

    def process_next_category(self, spider):
        if not self.processed_next_categories:
            self.processed_next_categories = True
            r = Request(self.start_urls[0], callback=self.parse2, dont_filter=True)
            self.crawler.engine.crawl(r, self)

    def parse(self, response):
        for url in response.xpath('//ul[@class="col-xs-12 menu-margin"]//li/a/@href').extract():
            if url.endswith("football"):
                # skip "All football" category
                continue
            if url.endswith("printed-shirts"):
                # skip "Printed Shirts" category
                continue
            yield Request(response.urljoin(url), callback=self.parse_products)

    def parse2(self, response):
        for url in response.xpath('//ul[@class="col-xs-12 menu-margin"]//li/a/@href').extract():
            if not url.endswith("printed-shirts"):
                # skip "Printed Shirts" category
                continue
            yield Request(response.urljoin(url), callback=self.parse_products)

    def parse_products(self, response):
        categories = response.xpath("//div[contains(@class, 's-breadcrumbs-bar')]//ol/li//text()").extract()[1:]
        products = response.xpath('//*[@id="productlistcontainer"]//li[@li-productid]//'
                                  'div[contains(@class, "productimage")]//a[1]/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product,
                          meta={'categories': categories})

        subcats = response.xpath("//div[@class='categoryListSide']/ul/li/a/@href").extract()
        for url in subcats:
            yield Request(response.urljoin(url), callback=self.parse_products)

        pages = response.xpath('//*[@id="TopPaginationWrapper"]//a/@href').extract()
        for url in pages:
            yield Request(response.urljoin(url), callback=self.parse_products)

        if not products and not subcats and 'SearchNoResults'.lower() not in response.url.lower():
            yield Request(response.url, dont_filter=True, callback=self.parse_product,
                          meta={'categories': response.meta.get('categories')})

    def parse_product(self, response):
        data_layer = response.xpath("//script[contains(text(), 'dataLayer.push')]").re('dataLayer.push\((.*)\);')[0]
        data = json.loads(data_layer.replace("'", '"'))
        name = data['productName']
        identifier = data['productId']
        sku = identifier
        # price = data['productPrice']
        brand = data['productBrand']
        categories = response.meta.get('categories')
        if not categories:
            categories = response.xpath("//div[contains(@class, 's-breadcrumbs-bar')]//ol/li/a/text()").extract()[1:]

        for variants in json.loads(response.xpath("//*[contains(@class,'ProductDetailsVariants')]/@data-variants").extract_first()):
            image_url = variants['ProdImages']['ImgUrl']

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            # loader.add_value('identifier', identifier)
            colvarid = variants['ColVarId']
            item_url = add_or_replace_parameter(response.url, 'colcode', colvarid)
            loader.add_value('url', item_url)
            loader.add_value('sku', sku)
            loader.add_value('category', categories)
            loader.add_value('brand', brand)
            # loader.add_value('url', response.url)
            loader.add_value('image_url', response.urljoin(image_url))
            # loader.add_value('price', extract_price(price))
            loader.add_value('shipping_cost', Decimal("4.99"))
            item = loader.load_item()

            for size in variants['SizeVariants']:
                identifier = size['SizeVarId']
                option_item = item.copy()
                option_item['identifier'] = identifier
                size_name = size['SizeName']
                option_item['price'] = Decimal(size['ProdSizePrices']['SellPrice'].replace(u'£', ''))

                if response.xpath("//*[@class='personaliseSize']"):
                    url = personalise_url.format(identifier)
                    yield Request(url, callback=self.parse_personalise, meta={'item': option_item, 'size': size_name})

                # base product
                option_item = item.copy()
                option_item['identifier'] = identifier
                size_name = size['SizeName']
                option_item['price'] = Decimal(size['ProdSizePrices']['SellPrice'].replace(u'£', ''))
                option_item['name'] += u' ({})'.format(size_name)
                loader = ProductLoader(item=option_item, response=response)
                new_item = loader.load_item()
                new_item['metadata'] = {'size': SIZE_MAP.get(size_name, size_name)}
                yield new_item

    def parse_personalise(self, response):
        item = response.meta['item']
        size = response.meta['size']
        letter_price = response.xpath("//div[@id='divLetters']/span[@class='personalisationnote']/text()").re(u'£(\d*) per character')
        try:
            letter_price = Decimal(letter_price[0])
        except IndexError:
            return
        number_price = response.xpath("//div[@id='divNumbers']/span[@class='personalisationnote']/text()").re(u'£(\d*) per digit')
        number_price = Decimal(number_price[0])
        badges = response.xpath("//div[@id='divMinimum']/span[@class='personalisationnotecheck']/text()").re(u'£(\d*) for (.*)$')
        if badges:
            badges_name = badges[1]
            badges_price = Decimal(badges[0])
        if len(badges) > 2:
            self.errors.append("WARNING! Several badges found in product: {}".format(item['url']))

        for option in response.xpath("//select[@id='pListClubPlayer']/option/text()").extract():
            if not option:
                continue
            option_item = item.copy()
            option_item['name'] += ' - {} ({})'.format(option, size)
            option_item['identifier'] += ':' + option.strip().lower()

            number = option.split()[0]
            player = ' '.join(option.split()[1:])
            option_item['price'] += letter_price * len(player.replace(' ', '')) + number_price * len(number)

            loader = ProductLoader(item=option_item, response=response)
            product = loader.load_item()
            product['metadata'] = {
                'player': player,
                'number': number,
                'size': SIZE_MAP.get(size, size),
            }
            yield product
