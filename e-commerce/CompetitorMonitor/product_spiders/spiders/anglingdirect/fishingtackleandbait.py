import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter

from product_spiders.items import Product, ProductLoader
from scrapy.http import FormRequest

from product_spiders.utils import extract_price


class Fishingtackleandbait(BaseSpider):
    name = 'anglingdirect-fishingtackleandbait.co.uk'
    allowed_domains = ['fishingtackleandbait.co.uk']
    start_urls = ('https://www.fishingtackleandbait.co.uk/SetProperty.aspx?languageiso=en&currencyiso=GBP&shippingcountryid=1903',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        yield Request('https://www.fishingtackleandbait.co.uk', callback=self.parse_products)

    def parse_products(self, response):

        # categories
        category_urls = response.xpath('//ul[@class="tab-list"]//a/@href').extract()
        category_urls += response.xpath('//a[@class="brand-link"]/@href').extract()
        for url in category_urls:
            yield Request(response.urljoin(url), callback=self.parse_products)

        # products
        products = response.xpath('//div[contains(@class, "model-link-container")]/a/@href').extract()
        for url in products:
            url = response.urljoin(url)
            yield Request(url, callback=self.parse_product)

        next_url = response.xpath('//a[contains(text(), "Next")]/@href').extract()
        if next_url:
            yield Request(response.urljoin(next_url[0]), callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        category = response.xpath('//table[@class="history-menu-table"]//a/text()').extract()[1:-2]
        image_url = response.xpath('//img[@id="ModelsDisplayStyle1_ImgModel"]/@src').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''

        product_brand = response.xpath('//a[@class="brand-image-link"]/@title').extract()
        product_brand = product_brand[0].strip() if product_brand else ''

        shipping_cost = response.xpath('//span[@id="ModelsDisplayStyle1_LblPostageCostValue"]/text()').extract()
        shipping_cost = extract_price(shipping_cost[0]) if shipping_cost else 0

        name = ' '.join(response.xpath('//h1/span[not(@class="models-page-title-price")]/text()').extract())
        options = response.xpath('//tr[contains(@class, "item-row")]')
        if options:
            # options
            for option in options:
                name2 = option.xpath('.//a[contains(@class, "option-text")]/text()').extract()
                if not name2:
                    name2 = option.xpath('.//span[contains(@class, "option-text")]/text()').extract()
                option_name = name + ' ' + name2[0].strip() if name2 else name

                price = option.xpath('.//span[contains(@class, "price-label")]/text()').extract()[0]
                sku = option.xpath('.//td[contains(@class, "item-part-code")]/text()').extract()[0].strip()

                identifier = option.xpath('.//a[@class="add-to-basket-button"]/@href').re('StockID=(\d+)')
                if not identifier:
                    identifier = option.xpath('.//a[@class="request-stock-alert-link"]/@onclick').re('StockID=(\d+)')
                identifier = identifier[0]
                loader = ProductLoader(item=Product(), selector=option)
                loader.add_xpath('identifier', identifier)
                loader.add_value('sku', sku)
                loader.add_value('url', response.url)
                loader.add_value('name', option_name)
                loader.add_value('price', price)
                loader.add_value('category', category)
                loader.add_value('image_url', image_url)
                loader.add_value('brand', product_brand)
                in_stock = option.xpath('.//td[contains(@class, "item-in-stock")]')
                if not in_stock:
                    loader.add_value('stock', 0)
                else:
                    stock_level = in_stock.re('\d+')
                    if stock_level:
                        loader.add_value('stock', int(stock_level[0]))
                if loader.get_output_value('price') < 50:
                    loader.add_value('shipping_cost', shipping_cost)

                yield loader.load_item()

        if not options:
            options = response.xpath('//input[contains(@id, "HidStockOptionDetails")]')
            if options:
                for option in options:
                    option_data = json.loads(option.xpath('@value').extract()[0])
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('url', response.url)
                    loader.add_value('name', name + ' ' + option_data['option'])
                    loader.add_value('price', extract_price(str(option_data['price'])))
                    loader.add_value('identifier', option_data['stockID'])
                    loader.add_value('image_url', image_url)
                    loader.add_value('category', category)
                    loader.add_value('sku', option_data['partcode'])
                    loader.add_value('brand', product_brand)
                    stock_level = re.findall('\d+', json.loads(option.xpath('@value').extract()[0])['stockLevelText'])
                    if stock_level:
                        loader.add_value('stock', int(stock_level[0]))
                    else:
                        self.log('POSSIBLE OUT OF STOCK : ' + response.url)
                    if loader.get_output_value('price') < 50:
                        loader.add_value('shipping_cost', shipping_cost)
                    yield loader.load_item()
            else:
                self.log(' >>> NO OPTIONS FOUND: ' + response.url)
                price = "".join(hxs.select(".//span[@class='bigprice']/text()").re(r'([0-9\,\. ]+)')).strip()
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('price', price)
                loader.add_value('identifier', response.url)
                loader.add_value('image_url', image_url)
                loader.add_value('category', category)
                loader.add_xpath('sku', './td[position()=2]/text()')
                loader.add_value('brand', product_brand)
                if loader.get_output_value('price') < 50:
                    loader.add_value('shipping_cost', shipping_cost)
                yield loader.load_item()

