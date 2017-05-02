from decimal import Decimal

from utils import extract_price

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from scrapy import log

from product_spiders.items import Product, \
    ProductLoaderWithNameStrip as ProductLoader


class GardenSiteSpider(BaseSpider):
    name = 'gardensite.co.uk'
    allowed_domains = ['gardensite.co.uk']
    start_urls = ['http://www.gardensite.co.uk/Aquatics/']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[@class="top_menu"]//a[contains(@class, "active")]'
                                '/following-sibling::div//a/@href').extract()
        # Categories that are not currently visible in the site menu
        categories.extend(['http://www.gardensite.co.uk/Blagdon_Shop/',
                           'http://www.gardensite.co.uk/Evolution_Aqua_Shop/',
                           'http://www.gardensite.co.uk/Buy_Pond_Fish_Online/',
                           'http://www.gardensite.co.uk/Aquatics/Reptile_Shop/',
                           'http://www.gardensite.co.uk/Hozelock_Watering/',
                           ])
        for category in categories:
            url = urljoin_rfc(base_url, category)
            yield Request(url, callback=self.parse_categories)

    def parse_categories(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        products = []

        categories = hxs.select('//ul[@class="side_menu_group"]'
                                '/li/a/@href').extract()
        products = hxs\
            .select('//div[contains(@class, "splash_wrapper")]'
                    '//h2[@class="splash_prod_title"]/a/@href').extract()

        for product_url in products:
            yield Request(urljoin_rfc(base_url, product_url),
                          callback=self.parse_product)
        for category in categories:
            yield Request(urljoin_rfc(base_url, category),
                          callback=self.parse_categories)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        main_price = hxs.select('//input[@id="price"]/@value').extract()

        products = hxs.select('//div[@class="complex_title"]')

        try:
            sku = hxs.select('//span[@class="product_code"]/text()')\
                .re(r'\((.*)\)')[0].strip()
        except:
            try:
                sku = hxs.select('//span[@class="product_code"]/text()')\
                    .re(r'EAN:(.*)')[0].strip()
            except:
                sku = ''

        try:
            image = hxs.select('//img[contains(@id, "optimised_image")]'
                                   '/@src').extract()[0].strip()
        except:
            try:
                image = hxs.select('//a[@id="thumb"]/img/@src')\
                    .extract()[0].strip()
            except:
                try:
                    image = hxs.select('//img[contains(@id, "main_image")]'
                                       '/@src').extract()[0].strip()
                except:
                    image = None

        if image:
            image = urljoin_rfc(base_url, image)

        try:
            product_name = hxs.select('//h1[@class="details_title"]/text()')\
                .extract()[0].strip()
        except:
            try:
                product_name = hxs.select('//div[contains(@class, "content_box")]/h1'
                                          '/text()').extract()[0].strip()
            except:
                product_name = ''

        sub_id = sku if sku else product_name

        collected = False

        if products:

            if main_price:
                main_price = Decimal(main_price[0])

                identifier = hxs.select('//input[@name="productID"]/@value').extract()[0].strip()

                if main_price:
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('sku', sku)
                    loader.add_value('identifier', sub_id + identifier)
                    loader.add_value('name', product_name)
                    loader.add_value('url', response.url)
                    loader.add_value('price', main_price)
                    loader.add_value('image_url', image)
                    yield loader.load_item()

            for product in products:
                price = ''.join(product
                                    .select('following-sibling::*'
                                            '[@class="complex_price"]/text()')
                                    .extract()).strip()
                if price:
                    collected = True

                    if main_price:
                        price = Decimal(extract_price(price)) + main_price

                    name = product_name + ' ' + \
                        ''.join(product
                                .select('./text()')
                                .extract()).strip().replace(product_name, '')

                    identifier = product.select('preceding-sibling::'
                                                '*[@class="image_float_left"]'
                                                '/input[@type="radio" or '
                                                '@type="checkbox"]'
                                                '/@value')\
                                                .re(r'(.*)@.*@.*')[0].strip()
                    loader = ProductLoader(response=response,
                                           item=Product())
                    loader.add_value('sku', sku)
                    loader.add_value('identifier', sub_id + identifier)
                    loader.add_value('name', name)
                    loader.add_value('url', response.url)
                    loader.add_value('price', price)
                    loader.add_value('image_url', image)
                    yield loader.load_item()

        if not collected:
            products = hxs.select('//div[@id="group_cell_container"]'
                                  '//div[@class="group_cell"]'
                                  '//div[@class="group_cell"]')
            if not products:
                products = hxs.select('//div[@class="group_cell"]/div')

            if products:
                for product in products:
                    identifier = product\
                        .select('.//div[@class="image_float_left"]'
                                '/input[@type="radio"]/@value').extract()
                    price = ''.join(product
                                    .select('div[@class="complex_price"]'
                                            '/text()').extract()).strip()

                    name = product_name + ' ' + \
                        ''.join(product
                                .select('div[@class="complex_title"]/text()')
                                .extract()).strip().replace(product_name, '')
                    if price:
                        collected = True
                        loader = ProductLoader(item=Product(), selector=product)
                        loader.add_value('sku', sku)
                        loader.add_value('identifier', sub_id + identifier[0].strip())
                        loader.add_value('name', name)
                        loader.add_value('url', response.url)
                        loader.add_xpath('price', 'div[@class="complex_price"]'
                                         '/text()')
                        loader.add_value('image_url', image)
                        yield loader.load_item()

            if not collected:
                try:
                    name = hxs.select('//h1[@class="details_title"]'
                                      '/text()').extract()[0].strip()
                except:
                    name = hxs.select('//div[contains(@class, "content_box")]/h1'
                                      '/text()').extract()[0].strip()

                try:
                    identifier = hxs.select('//input[@name="productID"]/@value')\
                        .extract()[0].strip()
                except:
                    identifier = ''

                url = response.url

                try:
                    price = hxs.select('//span[@id="final_price"]/text()')\
                        .extract()[0].strip()
                except:
                    price = None

                if price:
                    collected = True
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('sku', sku)
                    loader.add_value('name', name)
                    loader.add_value('identifier', sub_id + identifier.strip())
                    loader.add_value('url', response.url)
                    loader.add_value('price', price)
                    loader.add_value('image_url', image)

                    yield loader.load_item()

            if not collected:
                log.msg('NOT SCRAPPED!!! : ' + response.url)
