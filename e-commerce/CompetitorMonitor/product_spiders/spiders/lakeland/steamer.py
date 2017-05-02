from decimal import Decimal
from scrapy import Request
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.base_spiders import PrimarySpider
from product_spiders.items import Product, ProductLoader
from product_spiders.lib.schema import SpiderSchema


class SteamerSpider(PrimarySpider):
    name = 'lakeland-steamer.co.uk'
    allowed_domains = ['steamer.co.uk']
    csv_file = 'lakeland_steamer_as_prim.csv'
    start_urls = ['http://www.steamer.co.uk/productAZ']

    def parse(self, response):
        links = response.xpath('//ul/li/a/@href').extract()
        for link in links:
            yield Request(response.urljoin(link), callback=self.parse_listing)

    def parse_listing(self, response):
        prod_links = response.xpath('//div[@class="category-products"]//h2[@class="product-name"]/a/@href').extract()
        if not prod_links:
            return
        for link in prod_links:
            yield Request(response.urljoin(link), callback=self.parse_product)
        go_next_page = len(set(response.xpath('//div[@class="pager"]/p[@class="amount"]/text()')
                               .re(r'(\d+) of (\d+) total'))) > 1
        if go_next_page:
            next_page = response.meta.get('page', 1) + 1
            url = add_or_replace_parameter(response.url, 'is_ajax', '0')
            url = add_or_replace_parameter(url, 'p', str(next_page))
            yield Request(
                url,
                callback=self.parse_listing,
                meta={'page': next_page}
            )

    def parse_product(self, response):
        schema = SpiderSchema(response)
        product_data = schema.get_product()
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', product_data['productID'])
        loader.add_value('sku', product_data['productID'])
        loader.add_value('name', product_data['name'])
        out_stock = bool(response.css('.product-shop .out-of-stock'))
        if (not out_stock) and ('InStock' in product_data['offers']['properties']['availability']):
            loader.add_value('stock', 1)
        else:
            loader.add_value('stock', 0)
        category = response.css('.breadcrumbs').xpath('.//li/a/text()').extract()[1:]
        loader.add_value('category', category)
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        loader.add_xpath('brand', '//th[@class="label" and contains(text(), '
                         '"Brand")]/following-sibling::td/text()')
        price = response.css('.product-shop .price-box .minimal-price .price').xpath('text()').re_first(r'[\d\.,]+')
        if not price:
            price = response.css('.product-shop .price-box .regular-price .price').xpath('text()').re_first(r'[\d\.,]+')
        if not price:
            price = response.css('.product-shop .price-box .special-price .price').xpath('text()').re_first(r'[\d\.,]+')
        loader.add_value('price', price)

        if loader.get_output_value('price') >= Decimal('45.0'):
            loader.add_value('shipping_cost', '0.0')
        else:
            loader.add_value('shipping_cost', '4.95')

        yield loader.load_item()

        for url in response.css('.grouped-items-table-wrapper .name-wrapper').xpath('a/@href').extract():
            yield Request(url, callback=self.parse_product)
