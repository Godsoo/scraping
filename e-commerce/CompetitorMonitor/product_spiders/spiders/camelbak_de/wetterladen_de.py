import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.utils.url import add_or_replace_parameter
import itertools


class WetterladenSpider(scrapy.Spider):
    name = 'camelbak_de-wetterladen.de'
    allowed_domains = ['wetterladen.de']
    start_urls = ('http://www.wetterladen.de/search?sSearch=CamelBak&p=1&n=9999',)

    def parse(self, response):
        products = response.xpath('//a[@class="product--title"]/@href').extract()
        for url in products:
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)

        name = response.xpath('//h1[@itemprop="name"]/text()').extract_first()
        identifier = response.xpath('//input[@name="sAdd"]/@value').extract_first()
        image_url = response.xpath('//img[@itemprop="image"]/@srcset').extract_first()
        price = response.xpath('//meta[@itemprop="price"]/@content').extract_first()
        stock = response.xpath('//button[@name="In den Warenkorb"]')

        #check for options
        options = response.xpath('//div[@class="product--configurator"]')
        if options:
            option_elements = []
            for selector in options.xpath('.//select'):
                options = []
                group = selector.xpath('./@name').extract_first()
                for dropdown_option in selector.xpath('.//option'):
                    option = dict()
                    option['name'] = dropdown_option.xpath('./text()').extract_first()
                    option['selected'] = dropdown_option.xpath('./@selected').extract_first() is not None
                    option['group_value'] = dropdown_option.xpath('./@value').extract_first()
                    option['group'] = group
                    options.append(option)
                option_elements.append(options)
            if option_elements:
                combined_options = list(itertools.product(*option_elements))
                for combined_option in combined_options:
                    final_option = dict()
                    final_option['url'] = add_or_replace_parameter(response.url, 'template', 'ajax')
                    for option in combined_option:
                        final_option['name'] = final_option.get('name', '') + ' ' + option['name']
                        final_option['url'] = add_or_replace_parameter(final_option['url'],
                                                                       option['group'],
                                                                       option['group_value'])
                        final_option['selected'] = final_option.get('selected', True) and option['selected']
                    if not response.meta.get('lvl2'):
                        yield scrapy.Request(final_option['url'],
                                             callback=self.parse_product,
                                             meta={'lvl2': True, 'url': response.url})
                    elif final_option['selected']:
                        name = name + final_option['name']

        loader.add_value('name', name)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('brand', 'CamelBak')
        if response.meta.get('lvl2'):
            loader.add_value('url', add_or_replace_parameter(response.meta.get('url'), 'number', identifier))
        else:
            loader.add_value('url', response.url)
        loader.add_value('image_url', image_url)
        loader.add_value('category', 'Freizeit-Outdoor-Sport')
        loader.add_value('price', price)
        if not stock:
            loader.add_value('stock', 0)

        yield loader.load_item()
