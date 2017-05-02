import os
import re
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.http import Request, HtmlResponse

from product_spiders.items import (Product,
									ProductLoaderWithNameStrip as ProductLoader)

HERE = os.path.abspath(os.path.dirname(__file__))


class Fishingtackle2goSpider(BaseSpider):
    name = 'nash_tackle-fishingtackle2go.co.uk'
    allowed_domains = ['fishingtackle2go.co.uk']
    start_urls = ('http://www.fishingtackle2go.co.uk/',)

    shipping_cost = Decimal('6.95')

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        categories = response.xpath('//div[@id="mega-wrapper"]//ul/li[not(@class) and not(@id)]/a')
        for category in categories:
            category_url = response.urljoin(category.xpath('@href')[0].extract())
            req = Request(url=category_url, callback=self.parse_category)
            req.meta['category'] = category.xpath('text()')[0].extract()
            yield req

    def parse_category(self, response):
        if not isinstance(response, HtmlResponse):
            return
        products = response.xpath('//div[@id="productListing"]//h3[@class="itemTitle"]/a/@href').extract()
        for product in products:
            yield Request(url=response.urljoin(product), callback=self.parse_product, meta=response.meta)
        next_page = response.xpath('//div[@id="productsListingListingBottomLinks"]/a[contains(text(), "Next")]/@href').extract()
        if next_page:
            yield Request(url=response.urljoin(next_page[0]), callback=self.parse_category, meta=response.meta)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        options = response.xpath('//div[@class="optionValues"]/select/option')
        name = response.xpath('//div[@id="productGeneral"]/form//h1[@id="productName"]/text()').extract()

        price = response.xpath('//div[@id="productGeneral"]/form//h2[@id="productPrices"]/span[@class="productSalePrice"]/text()').extract()
        if not price:
            price = response.xpath('//div[@id="productGeneral"]/form//h2[@id="productPrices"]/span[@class="productSpecialPrice"]/text()').extract()
        if not price:
            price = response.xpath('//div[@id="productGeneral"]/form//h2[@id="productPrices"]/text()').extract()
        if price:
            price = price[0]
        price = price.replace(',', '').strip()
        stock = response.xpath('//div[@id="cartAdd"]/input[@class="cssButton button_in_cart"]')
        if not stock:
            stock = 0
        category = response.meta['category'].replace(u'/', u' > ')
        
        brand = response.xpath('//ul[@id="productDetailsList"]/li/text()').re('Manufactured by: (.*)')

        gtin_code = response.xpath('//ul[@id="productDetailsList"]/li/text()').re('GTIN: (.*)')
        model_code = response.xpath('//ul[@id="productDetailsList"]/li/text()').re('Model: (.*)')

        image_url = response.xpath('//div[@class="MagicToolboxContainer"]/a/img/@src').extract()
        if image_url:
            image_url = response.urljoin(image_url[0])

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('price', price)
        price = Decimal(loader.get_output_value('price'))
        if price < Decimal('100.0'):
            loader.add_value('shipping_cost', self.shipping_cost)
        if not stock:
            loader.add_value('stock', 0)
        loader.add_value('category', category)
        loader.add_value('brand', brand)
        identifier = response.xpath('//input[@name="products_id"]/@value')[0].extract()

        loader.add_value('sku', gtin_code[0] if gtin_code else model_code[0])
        loader.add_value('url', response.url)
        loader.add_value('image_url', image_url)
        loader.add_value('name', name)
        loader.add_value('identifier', identifier)

        if options:
            for option in options:
                option_id = option.xpath('@value')[0].extract()
                loader.replace_value('identifier', identifier + u'_' + option_id)
                option_name = option.xpath('text()')[0].extract()
                option_price = re.search('\( \+(.*)', option_name)
                loader.replace_value('name', u'{} {}'.format(name, option_name))
                if option_price:
                    option_price = option_price.group(1)
                    option_price = re.search('([\.\d]+)', option_price.replace(',', '')).group(1)
                    new_price = price + Decimal(option_price)
                    if new_price < Decimal('100'):
                        loader.replace_value('shipping_cost', self.shipping_cost)
                    else:
                        loader.replace_value('shipping_cost', Decimal('0.00'))
                    loader.replace_value('price', new_price)
                    loader.replace_value('name', u'{} {}'.format(name, option_name))
                yield loader.load_item()
        else:
            yield loader.load_item()
