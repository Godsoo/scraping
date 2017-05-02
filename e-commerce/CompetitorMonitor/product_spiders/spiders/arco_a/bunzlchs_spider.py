from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import itertools


class BunzlchsSpider(BaseSpider):
    name = 'arco-a-bunzlchs.com'
    allowed_domains = ['bunzlchs.com']
    start_urls = ('http://www.bunzlchs.com/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories_urls = hxs.select('//div[@id="nav_main"]//a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url))

        sub_categories = hxs.select('//div[@class="Item"]/a/@href').extract()
        sub_categories += hxs.select('//div[div/a/h4[contains(text(), "Category")]]//li/a/@href').extract()
        for url in sub_categories:
            yield Request(urljoin_rfc(base_url, url))

        products = hxs.select('//h3[@class="productName"]//a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next = hxs.select('//ul/li/a[contains(text(), "Next")]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sku =  hxs.select('//div[@class="prod"]/p[@class="code"]/text()').re('Code: (.*)')
        if sku:
            category = hxs.select('//div[@id="breadcrumb"]/ul/li/a/text()').extract()[-2]
            sku = sku[0].strip()
            product_loader = ProductLoader(item=Product(), selector=hxs)
            image_url = hxs.select('//img[@class="prod_primary_image"]/@src').extract()
            if image_url:
                image_url = urljoin_rfc(base_url, image_url[0])
            brand = ''.join(hxs.select('//div[@class="prod"]/h3/a[contains(@href, "Brand")]/text()').extract())
            

            product_loader.add_value('category', category)
            name = ''.join(hxs.select('//div[@class="prod"]/h3/label/text()').extract()).strip()
            option_name = ''.join(hxs.select('//div[contains(@class, "options")]/text()').extract()).strip()
            product_loader.add_value('name', name + ' ' + option_name)
            product_loader.add_value('url', response.url)
            product_loader.add_value('identifier', sku)

            product_loader.add_value('brand', brand)
            product_loader.add_value('sku', sku)
            product_loader.add_value('shipping_cost', '6')
            #stock = hxs.select('//span[@class="inStock"]/strong/text()').extract()

            price = hxs.select('//p[@class="big-price"]/span[@id="variant-price-header"]/text()').extract()
            if price:
                price = extract_price(price[0])
                product_loader.add_value('price', price)
            else:
                product_loader.add_value('price', 0)
                product_loader.add_value('stock', 0)
            product_loader.add_value('image_url', image_url)
            yield product_loader.load_item()


