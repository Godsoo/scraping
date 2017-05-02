from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price

import re, json


class PopfurnitureDeSpider(BaseSpider):

    name            = 'popfurniture_de'
    allowed_domains = ['popfurniture.com']
    start_urls      = ('http://www.popfurniture.com/pu_de/?___from_store=pu_en',)

    base_url = 'http://www.popfurniture.com'


    def parse(self, response):

        hxs = HtmlXPathSelector(response)

        categories = hxs.select("//ul[@id='nav']//li[not(@id='nav-home')]//a[not(@href='#')]/@href").extract()

        for category in categories:
            yield Request(category, callback=self.parse_pagination)


    def parse_pagination(self, response):

        hxs = HtmlXPathSelector(response)

        products = hxs.select("//div[@class='category-products']//li[@class='item']//h2[@class='product-name']/a/@href").extract()
        for url in products:
            yield Request(url, meta={'parse_options': True}, cookies={"currency": "EUR"}, callback=self.parse_product)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)

        if response.meta['parse_options']:
            color_options = hxs.select("//div[@class='more-colors']//a/@href").extract()
            for color in color_options:
                url = self.base_url + color
                yield Request(url, meta={'parse_options': False}, callback=self.parse_product)

        item_data = re.search('dataLayer.push\((.*)\);', response.body)
        item_data = json.loads(item_data.group(1))['ecommerce']['detail']['products'][0] if item_data else None

        name  = item_data.get('name')
        sku   = item_data.get('id')
        price = str(item_data.get('price'))
        price = float(extract_price(price))
        brand = item_data.get('brand')
        stock = 1 if price else 0
        brand = '' if brand == False else brand

        image_url    = ''.join(hxs.select("//img[@itemprop='image']/@src").extract())
        categories   = [category.strip() for category in hxs.select("//div[@class='breadcrumbs']//a/text()").extract()[1:]]
        categories   = [category for category in categories if not category.lower() in ['mehr', 'designer']]
        shipping     = 0

        color_swatches = re.search('ColorswatchConfig\((.*)\) ,', response.body)
        color_swatches = json.loads(color_swatches.group(1))['swatch'] if color_swatches else None

        if color_swatches:
            for color_swatch, colors in color_swatches.iteritems():
                for color_id, values in colors.iteritems():
                    #== If the next part throws an error, swatch is not available and we should skip it ==#
                    try:
                        option_name  = name + ' ' + values['option_values']['store_label']
                    except:
                        continue
                    option_id    = sku + values['option_values']['value_index']
                    option_price = values['option_values']['pricing_value']
                    if option_price:
                        option_price = 0 if option_price in ['null', 'None', None] else option_price
                        option_price = price + float(option_price)
                    else:
                        option_price = price

                    product_loader = ProductLoader(item=Product(), selector=hxs)
                    product_loader.add_value('image_url', image_url)
                    product_loader.add_value('shipping_cost', shipping)
                    product_loader.add_value('sku', option_id)
                    product_loader.add_value('url', response.url)
                    product_loader.add_value('name', option_name)
                    product_loader.add_value('brand', brand)
                    product_loader.add_value('identifier', option_id)
                    product_loader.add_value('price', option_price)
                    for category in categories:
                        if not category.lower() == 'more':
                            product_loader.add_value('category', category.strip())

                    yield product_loader.load_item()

        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('image_url', image_url)
            product_loader.add_value('shipping_cost', shipping)
            product_loader.add_value('sku', sku)
            product_loader.add_value('url', response.url)
            product_loader.add_value('name', name)
            product_loader.add_value('brand', brand)
            product_loader.add_value('identifier', sku)
            product_loader.add_value('price', price)
            for category in categories:
                if not category.lower() == 'more':
                    product_loader.add_value('category', category.strip())

            yield product_loader.load_item()