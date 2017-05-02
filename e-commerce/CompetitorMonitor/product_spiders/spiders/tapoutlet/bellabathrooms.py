import re
import json
import itertools
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log


class BellaBathroomsSpider(BaseSpider):
    name = 'bellabathrooms.co.uk'
    allowed_domains = ['bellabathrooms.co.uk']
    start_urls = ['http://www.bellabathrooms.co.uk/catalog/seo_sitemap/category']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select(u'//ul[@class="sitemap"]//a/@href').extract()

        for category in categories:
            yield Request(urljoin_rfc(get_base_url(response), category))

        for product in hxs.select(u'//a[div[@class="product-name-box"]]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product)

        for page in hxs.select(u'//a[@class="next i-next"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        category = hxs.select(u'//div[@class="breadcrumb"]/span/a/span/text()').extract()
        if category:
            category = category[-1]

        loader = ProductLoader(item=Product(), selector=hxs)

        identifier = hxs.select(u'//span[@itemprop="sku"]/text()')[0].extract()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier.replace(' ', ''))
        loader.add_value('url', response.url)
        name = hxs.select(u'//span[@itemprop="name"]/text()').extract()
        loader.add_value('name', name[0].strip())
        price = hxs.select(u'//span[@class="full-product-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select(u'//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select(u'//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        if not price or re.sub(u'[^\d\.]', u'', price[0].strip()) == '0.00':
            price = hxs.select(u'//div[@class="price-box-bundle"]').re(u'\xa3(.*?)<')
        price = re.sub(u'[^\d\.]', u'', price[0].strip())
        loader.add_value('price', str(round(Decimal(price) / Decimal(1.2), 2)))
        loader.add_value('category', category)

        img = hxs.select(u'//img[@itemprop="image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        brand = hxs.select(u'//th[text()="Manufacturer"]/following-sibling::td/text()').extract()
        if brand:
            brand = brand[0]
        else:
            brand = ''

        loader.add_value('brand', brand)
        i = 1


        option_lists = hxs.select(u'//ul[@class="options-list"]')
        option_lists += hxs.select('//dd/div[@class="input-box" and input]')
        option_elements = []
        options = []
        for option_list in option_lists:
            site_options = option_list.select('li')
            if not site_options:
                site_options = option_list.select('.')
            options = []
            for site_option in site_options:
                option = {}
                option_identifier = site_option.select(u'input/@value').extract()
                if option_identifier:
                    option['identifier'] = option_identifier[0]
                    option_price = site_option.select(u'.//span[@class="price-notice"]/span[@class="price"]/text()').extract()
                    if option_price:
                       option['price'] = Decimal(option_price[0].replace(u'\xa0', '').replace(u'\xa3', ''))
                    else:
                        option['price'] = Decimal(0)
                    option_description = site_option.select(u'.//span[@class="label"]/label/text()').extract()
                    if option_description:
                        option['desc'] = option_description[0].replace(u'\xa0', '')
                    else:
                        option['desc'] = ''.join(site_option.select('text()').extract()).strip()
                    options.append(option)
            option_elements.append(options)
        if option_elements:
            if len(option_elements)>1:
                combined_options = list(itertools.product(*option_elements))
                options = []
                for combined_option in combined_options:
                    final_option = {}
                    for option in combined_option:
                        final_option['desc'] = final_option.get('desc', '') + '- ' + option['desc']
                        final_option['price'] = final_option.get('price', 0) + Decimal(option['price'])
                        final_option['identifier'] = final_option.get('identifier', '') + '.' + option['identifier']
                    options.append(final_option)
            else:
                options = option_elements[0]
        option_elements = []
        options = []
        for option_list in option_lists:
            options = []
            site_options = option_list.select('li')
            for site_option in site_options:
                option = {}
                option['identifier'] = site_option.select(u'input/@value').extract()[0]
                option_price = site_option.select(u'.//span[@class="price-notice"]/span[@class="price"]/text()').extract()
                if option_price:
                   option['price'] = Decimal(option_price[0].replace(u'\xa0', '').replace(u'\xa3', ''))
                option['desc'] = site_option.select(u'.//span[@class="label"]/label/text()').extract()[0].replace(u'\xa0', '')
                options.append(option)
            option_elements.append(options)
        if option_elements:
            if len(option_elements)>1:
                combined_options = list(itertools.product(*option_elements))
                options = []
                for combined_option in combined_options:
                    final_option = {}
                    for option in combined_option:
                        final_option['desc'] = final_option.get('desc', '') + ' - ' + option['desc']
                        final_option['price'] = final_option.get('price', 0) + Decimal(option['price'])
                        option_identifier = final_option.get('identifier', '')
                        if option_identifier:
                            final_option['identifier'] = final_option.get('identifier', '') + '.' + option['identifier']
                        else:
                            final_option['identifier'] = option['identifier']
                    options.append(final_option)
            else:
                options = option_elements[0]
        if options:
            for option in options:
                loader = ProductLoader(item=Product(), selector=option)
                identifier = hxs.select(u'//span[@itemprop="sku"]/text()')[0].extract()
                loader.add_value('identifier', u'%s.%s' % (identifier, option['identifier']))
                loader.add_value('sku', identifier.replace(' ', ''))
                loader.add_value('url', response.url)
                name = hxs.select(u'//span[@itemprop="name"]/text()').extract()[0]
                option_desc = option['desc']
                loader.add_value('name', name + option_desc)
                option_price = option['price']
                if not option_price:
                    continue
                price = Decimal(price)
                loader.add_value('price', round(option_price / Decimal(1.2), 2))
                loader.add_value('category', category)
                loader.add_value('brand', brand)
                if img:
                    loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
                yield loader.load_item()
                i += 1
        else:
            yield loader.load_item()
