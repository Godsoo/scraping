from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import itertools


class SafetysuppliesCoUkSpider(BaseSpider):
    name = 'safetysupplies.co.uk'
    allowed_domains = ['safetysupplies.co.uk']
    start_urls = ('http://www.safetysupplies.co.uk/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #check for new categories
        categories_urls = hxs.select('/html/body/table/tr/td[1]/p/a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        category = hxs.select('//h3/text()').extract()[0]

        #check for subcategories
        categories_urls = hxs.select('/html/body/table/tr/td[3]/font/table[2]//tr//a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

        products = hxs.select('//form')
        for product in products:
            product_identifier = product.select('./@id').extract()[0]
            product_name = product.select('./table/tr[1]/td/font/b/text()[1]').extract()[0]
            image_url = product.select('./table/tr[2]/td/img/@src').extract()[0]
            price = product.select('./table/tr[1]/td/font/b/text()[3]').extract()[0]
            price = extract_price(price)
            #exclude VAT
            #price = round(float(price) / 1.2, 2)
            options = product.select('.//select')
            if options:
                #multiple options product
                variations_list = []
                #first, create all possible options list from all options we can find
                for option in options:
                    options_list = []
                    option_values = option.select('.//option')
                    for value in option_values:
                        value_code = value.select('./@value').extract()[0].replace(' ', '-')
                        if not value_code:
                            continue
                        value_name = value.select('./text()').extract()[0]
                        options_list.append({'code': value_code, 'name': value_name})
                    variations_list.append(options_list)
                #iterate over all variations
                for variation in itertools.product(*variations_list):
                    name = product_name
                    identifier = product_identifier
                    for option in variation:
                        name += ', ' + option['name']
                        identifier += '-' + option['code']
                    product_loader = ProductLoader(item=Product(), selector=hxs)
                    product_loader.add_value('category', category)
                    product_loader.add_value('name', name)
                    product_loader.add_value('url', response.url)
                    product_loader.add_value('identifier', identifier)
                    product_loader.add_value('sku', '')
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
                    product_loader.add_value('price', price)
                    product = product_loader.load_item()
                    yield product
            else:
                #single options product
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('category', category)
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
                product_loader.add_value('name', product_name)
                product_loader.add_value('url', response.url)
                product_loader.add_value('identifier', product_identifier)
                product_loader.add_value('sku', '')
                product_loader.add_value('price', price)
                product = product_loader.load_item()
                yield product