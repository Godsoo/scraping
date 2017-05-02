from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import itertools

from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.contrib.spiders.sitemap import SitemapSpider

class BigDugSpider(PrimarySpider, SitemapSpider):
    name = 'arco-a-bigdug.co.uk'
    allowed_domains = ['bigdug.co.uk']
    # start_urls = ('http://www.bigdug.co.uk',)
    sitemap_urls = ['http://www.bigdug.co.uk/sitemap-categories.xml']
    # sitemap_follow = ['/sitemap-products']
    sitemap_rules = [
        ('/', 'parse_product_list'),
    ]

    csv_file = 'bigdugcouk_crawl.csv'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories_urls = hxs.select('//td/a[contains(@class, "header_menu_link")]/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories_urls = hxs.select('//div[@class="category_view"]/a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

        products_urls = hxs.select('//div[contains(@class, "product ")]/ul/li[@class="product_image"]/a/@href').extract()
        for url in products_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        next = hxs.select('//a[@class="next_page page_num"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category = hxs.select('//div[@id="breadcrumb_container"]/p/span/a/text()').extract()[-1]

        options = hxs.select('//div[@id="main_overview_tab_content"]/table[@class="product_table_options"]/tr[@class="row_alt" or @class="row"]')
        for option in options:
            product_loader = ProductLoader(item=Product(), selector=option)
            product_id = option.select('td/input[@class="quantity_textbox"]/@id').extract()[0].split('_')[-1]
            image_url = hxs.select('//div[@id="product_img"]/a/img/@src').extract()
            if image_url:
                image_url = urljoin_rfc(base_url, image_url[0])
            brand = hxs.select('//img[@class="brandImageMedium"]/@alt').extract()
            brand = brand[0].replace(' logo', '') if brand else ''
            sku = option.select('td[@class="product_code"]/text()').extract()[-1]

            product_loader.add_value('category', category)
            name = option.select('td[@class="product_title"]/span/text()').extract()
            if not name:
                name = option.select('td[@class="product_title"]/text()').extract()

            product_loader.add_value('name', name[0].strip())
            product_loader.add_value('url', response.url)
            product_loader.add_value('identifier', product_id)

            # product_loader.add_value('brand', brand)
            product_loader.add_value('sku', sku)
            in_stock = option.select('td/input[contains(@class, "add_bag_btn")]')

            if not in_stock:
                product_loader.add_value('stock', 0)

            price = option.select('td//span[@class="price"]/span[@class="ex"]/span[@class="GBP"]/text()').extract()
            if price:
                price = extract_price(price[0])
                product_loader.add_value('price', price)
            else:
                product_loader.add_value('price', 0)

            shipping_cost = None

            if price <= 9:
                shipping_cost = 3
            elif price >= 10 and price <= 49:
                shipping_cost = 10
            elif price >= 50 and price <= 99:
                shipping_cost = 20
            elif price >= 100 and price <= 199:
                shipping_cost = 30
            elif price >= 200 and price <= 399:
                shipping_cost = 40
            elif price >= 400 and price <= 599:
                shipping_cost = 50
            elif price >= 600 and price <= 799:
                shipping_cost = 70
            elif price >= 800 and price <= 999:
                shipping_cost = 90
            elif price >= 100:
                shipping_cost = (price * 10) / 100

            product_loader.add_value('shipping_cost', shipping_cost)


            product_loader.add_value('image_url', image_url)
            yield product_loader.load_item()


