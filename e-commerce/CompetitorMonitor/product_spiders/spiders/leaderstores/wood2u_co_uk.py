"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/5177

Extract all products including product options.
"""
import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import re
import itertools
from product_spiders.utils import extract_price


class ModadoorsSpider(scrapy.Spider):
    name = 'leaderstores-wood2u.co.uk'
    allowed_domains = ['wood2u.co.uk']
    start_urls = ('https://www.wood2u.co.uk/laminate.html?dir=desc&limit=all',
                  'https://www.wood2u.co.uk/engineered-wood-flooring.html?dir=desc&limit=all',
                  'https://www.wood2u.co.uk/solid-wood-flooring.html?dir=desc&limit=all',
                  'https://www.wood2u.co.uk/luxury-vinyl-tiles.html?dir=desc&limit=all',
                  'https://www.wood2u.co.uk/worktops-splashbacks-upstands.html?dir=desc&limit=all',
                  'https://www.wood2u.co.uk/waterproof-wall-panelling.html?dir=desc&limit=all',
                  'https://www.wood2u.co.uk/kitchen-taps-mixers.html?dir=desc&limit=all',
                  'https://www.wood2u.co.uk/wood-floor-accessories.html?dir=desc&limit=all',
                  'https://www.wood2u.co.uk/w2u-special-offers.html?dir=desc&limit=all')

    def parse(self, response):
        for url in response.xpath('//ul[@class="products-grid"]//li//h3/a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

    # @staticmethod
    def parse_product(self, response):
        name = response.xpath('//div[@class="product-name"]/h1/text()').extract_first()
        image_url = response.xpath('//a[@class="iwd_product_image"]/img/@src').extract_first()
        identifier = response.xpath('//input[@name="product"]/@value').extract_first()
        brand = response.xpath('//div[@class="box-brand"]/a/img/@alt').extract_first()
        price = response.xpath('//span[contains(@id, "price-including-tax-")]').css('div.hidden-price::text').extract_first() or response.xpath('//span[contains(@id, "price-including-tax-")]/text()').extract_first()
        sku = re.search(r"gts\.push\( \['google_base_offer_id', '(.*)'\]", response.body)
        if sku:
            sku = sku.groups()[0]
        options_containers = response.xpath('//select[contains(@name,"options[")]')
        if options_containers:
            combined_options = []
            for options_container in options_containers:
                element_options = []
                for option in options_container.xpath('./option[@value!=""]'):
                    option_id = option.xpath('./@value').extract_first()
                    option_name = option.xpath('./text()').extract_first()
                    element_options.append((option_id, option_name))
                combined_options.append(element_options)
            if len(options_containers) > 1:
                combined_options = list(itertools.product(*combined_options))
                for combined_option in combined_options:
                    option_name = name
                    option_id = identifier
                    option_price = extract_price(price)
                    for option in combined_option:
                        option_id += '_' + option[0]
                        if u'+\xA3' in option[1]:
                            n, p = option[1].split(u" +\xA3")
                            if u'(+\xA3' in p:
                                p = p.split(u'(+\xA3')[1].split()[0]
                                p = extract_price(p)
                            else:
                                p = 0
                            option_price += p
                            option_name += ' ' + n
                        else:
                            option_name += ' ' + option[1]
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('name', option_name)
                    loader.add_value('identifier', option_id)
                    loader.add_value('sku', sku)
                    loader.add_value('brand', brand)
                    loader.add_value('url', response.url)
                    loader.add_value('image_url', response.urljoin(image_url))
                    loader.add_value('price', option_price)
                    option_item = loader.load_item()
                    yield option_item
            else:
                for option in combined_options[0]:
                    option_name = name
                    option_id = identifier
                    option_price = extract_price(price)
                    option_id += '_' + option[0]
                    if u'+\xA3' in option[1]:
                        n, p = option[1].split(u" +\xA3")
                        if u'(+\xA3' in p:
                            p = p.split(u'(+\xA3')[1].split()[0]
                            p = extract_price(p)
                        else:
                            p = 0
                        option_price += p
                        option_name += ' ' + n
                    else:
                        option_name += ' ' + option[1]
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('name', option_name)
                    loader.add_value('identifier', option_id)
                    loader.add_value('sku', sku)
                    loader.add_value('brand', brand)
                    loader.add_value('url', response.url)
                    loader.add_value('image_url', response.urljoin(image_url))
                    loader.add_value('price', option_price)
                    option_item = loader.load_item()
                    yield option_item

        else:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('brand', brand)
            loader.add_value('url', response.url)
            loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('price', price)
            option_item = loader.load_item()
            yield option_item