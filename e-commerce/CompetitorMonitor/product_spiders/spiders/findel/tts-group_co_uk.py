"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/5096

Monitor all products. Extract all product options.
"""
import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import json
import itertools
from scrapy.utils.url import add_or_replace_parameter
import urlparse


class TtsGroupSpider(scrapy.Spider):
    name = 'findel-tts-group.co.uk'
    allowed_domains = ['tts-group.co.uk']
    start_urls = ('http://www.tts-group.co.uk/',)

    def parse(self, response):
        for url in response.xpath('//*[@id="navigation"]//ul[@class="menu-category level-1"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_category)

    def parse_category(self, response):
        for url in response.xpath('//div[@class="custom-left-nav"]/ul//a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_category)

        for url in response.xpath('//*[@id="search-result-items"]/li//a[@class="product-detail-link"]/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

        for url in response.xpath('//div[@class="pagination"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_category)

    def parse_product(self, response):
        identifier = response.xpath('//*[@id="pid"]/@value').extract_first()
        p_data = json.loads(response.xpath('//*[@id="product-data-{}"]/@value'.format(identifier)).extract_first())
        name = p_data['variant']
        stock = response.xpath('//*[@id="add-to-cart"]')
        price = p_data['price']
        brand = p_data['brand']
        category = response.xpath('//div[@class="breadcrumb"]//a/span/text()').extract()[1:]
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract_first()

        variations = response.xpath('//div[@class="product-variations"]/ul/li')
        url = response.meta.get('url', '')

        if variations and url == '':
            combined_options = []
            for variant in variations:
                element_options = []
                vtype = variant.xpath('./@class').extract_first()
                if vtype == 'attribute': # colour
                    vtitle = variant.xpath('./span/text()').extract_first()
                    if 'Select Colour' != vtitle:
                        self.log('Unknown vtitle: {} URL: {}'.format(vtitle, response.url))
                        return
                    for option in variant.xpath('./div/ul/li[@class="available"]'):
                        option_url = option.xpath('./a/@href').extract_first()
                        element_options.append(option_url)
                elif vtype == 'attribute variant-dropdown':
                    for option in variant.xpath('.//select[@class="variation-select"]/option')[1:]:
                        option_url = option.xpath('./@value').extract_first()
                        element_options.append(option_url)
                else:
                    self.log('Unknown vtype: {} URL: {}'.format(vtype, response.url))
                    return
                combined_options.append(element_options)

            if len(variations) > 1:
                combined_options = list(itertools.product(*combined_options))
                for combined_option in combined_options:
                    url = ''
                    for option in combined_option:
                        if url == '':
                            url = option
                        else:
                            params = dict(urlparse.parse_qsl(urlparse.urlsplit(option).query))
                            for name, value in params.iteritems():
                                url = add_or_replace_parameter(url, name, value)
                    yield scrapy.Request(url, callback=self.parse_product, meta={'url': response.url})
            else:
                for option in combined_options[0]:
                    yield scrapy.Request(option, callback=self.parse_product, meta={'url': response.url})

        else:
            if name == '':
                return
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            loader.add_value('category', category)
            if brand != 'Unbranded':
                loader.add_value('brand', brand)
            url = response.meta.get('url', response.url)
            loader.add_value('url', url)
            loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('price', price)
            if loader.get_output_value('price') <= 10:
                loader.add_value('shipping_cost', '1.50')
            elif loader.get_output_value('price') <= 200:
                loader.add_value('shipping_cost', '5.95')
            if not stock:
                loader.add_value('stock', 0)
            option_item = loader.load_item()
            yield option_item
