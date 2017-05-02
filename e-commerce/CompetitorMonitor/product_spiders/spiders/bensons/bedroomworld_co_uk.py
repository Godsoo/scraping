import re
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field
import json

from product_spiders.base_spiders.primary_spider import PrimarySpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class Meta(Item):
    net_price = Field()

class BedroomworldSpider(PrimarySpider):
    name = 'bedroomworld.co.uk'
    allowed_domains = ['bedroomworld.co.uk']
    start_urls = ['http://www.bedroomworld.co.uk/']

    csv_file = 'bedroomworld.co.uk_products.csv'

    products_extra = [
        'http://www.bedroomworld.co.uk/p/New_York_5_Chest_of_Drawers.htm',
        'http://www.bedroomworld.co.uk/p/Lakewood_Bed_Frame.htm',
        'http://www.bedroomworld.co.uk/p/Steens_Glossy_White_Tall_Bookcase.htm',
        'http://www.bedroomworld.co.uk/p/Hazel_Upholstered_Bedstead.htm',
    ]

    def start_requests(self):
        for url in self.products_extra:
            yield Request(url, callback=self.parse_product)

        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for cat_url in hxs.select('//ul[@id="menu"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, cat_url), callback=self.parse_cat)

        yield Request('http://www.bedroomworld.co.uk/brand_directory_list.php', callback=self.parse_brands)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for cat_url in hxs.select('//table[@class="mainbody_tablecat"]//td/a/@href').extract():
            yield Request(urljoin_rfc(base_url, cat_url), callback=self.parse_cat)

        for cat_url in hxs.select('//table[@class="tableLHSLinkContainer"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, cat_url), callback=self.parse_cat)

        if not hxs.select('//ul[@class="navigation"]//li[@class="checked"]'):
            for cat_url in hxs.select('//ul[@class="navigation"]//a/@href').extract():
                yield Request(urljoin_rfc(base_url, cat_url), callback=self.parse_cat)

        for url in hxs.select('//div[@class="item-name"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url.split('?')[0]), callback=self.parse_product)
        for url in hxs.select('//div[@class="pagination"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat)

    def parse_brands(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brands = hxs.select('//div[@class="brand_directory_list"]//td//a/@href').extract()

        for brand_url in brands:
            yield Request(urljoin_rfc(base_url, brand_url), callback=self.parse_cat)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        sku = hxs.select('//div[contains(@class, "order_code")]/text()').extract()
        sku = sku[0].split()[0] if sku else ''
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[contains(@class,"ws_product_details_item_name")]/text()')
        loader.add_xpath('category', '//div[contains(@class,"ws-breadcrumb")]/a[2]/text()')

        img = hxs.select('//img[@id="imageMain"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        brand = ''.join(hxs.select('//div[@class="ws_product_details_item_brand_image"]/img/@src').extract())
        loader.add_value('brand', brand.split('/')[-1].split('.')[0].replace('_', ' '))

        names = {}
        for opt in hxs.select('//option[@mcode]'):
            mcode = opt.select('./@mcode').extract()[0]
            text = opt.select('normalize-space(./text())').extract()[0]
            names[mcode] = text

        product = loader.load_item()

        options = re.search(r'qubit_product_list = {(.*)};$', response.body, flags=re.MULTILINE).group(1)
        options = json.loads("{%s}" % options)
        for identifier, option in options.items():
            prod = Product(product)
            prod['identifier'] = identifier
            prod['price'] = option.get("unit_sale_price") or option.get("unit_price")
            if option['stock']:
                prod['stock'] = 1
            else:
                prod['stock'] = 0
            prod['name'] = option['item_name'].strip()
            net_price = Decimal(prod['price']) / Decimal('1.2')
            meta_ = Meta()
            meta_['net_price'] = str(net_price)
            prod['metadata'] = meta_

            ajax_url = 'http://www.bedroomworld.co.uk/ajax.get_product.php'
            yield FormRequest(ajax_url, callback=self.parse_options, dont_filter=True, formdata={'product_id': identifier}, meta={'item':prod})

    def parse_options(self, response):
        json_data = json.loads(response.body)
        item = response.meta.get('item')
        prod_data = json_data['data']

        option_descriptions = prod_data['propertyType1']
        option_name = ''
        for option_desc in option_descriptions:
            if prod_data[option_desc].upper() not in item['name'].upper():
                option_name += ' ' + prod_data[option_desc]

        item['name'] += option_name

        yield item
