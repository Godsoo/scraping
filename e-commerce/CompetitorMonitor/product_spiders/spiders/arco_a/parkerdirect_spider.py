# from scrapy.spider import BaseSpider
from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
import itertools
import re


class ParkerDirectSpider(PrimarySpider):
    name = 'arco-a-parker-direct.com'
    allowed_domains = ['parker-direct.com']
    start_urls = ('http://www.parker-direct.com/',)

    csv_file = 'parker_crawl.csv'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories_urls = hxs.select('//ul[@class="level1"]/li/a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products_urls = hxs.select('//div/ol/li[contains(@class, "sku")]/div/h3/a/@href').extract()
        for url in products_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        next = hxs.select('//a[@rel="Next"]/@href').extract()
        if products_urls and next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        options = hxs.select('//select[@id="variant-select-size"]/option[text()!="-- Please select --"]/@value').extract()
        options += hxs.select('//select[@id="variant-select-colour"]/option[text()!="-- Please select --"]/@value').extract()

        for option in options:
            url = urljoin_rfc(base_url, option)
            yield Request(url, callback=self.parse_product)

        try:
            sku = hxs.select('//p[@id="brandAndPartNos"]/text()').extract()[-1].strip()
        except:
            retry = int(response.meta.get('retry', 0))
            if retry < 10:
                retry += 1
                new_meta = response.meta.copy()
                new_meta['retry'] = retry
                yield Request(response.url, meta=new_meta, callback=self.parse_product, dont_filter=True)
            return

        if sku or not options:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_id = hxs.select('//input[@name="productId"]/@value').extract()[0]
            name = hxs.select('//h1[@class="skuHeading"]/strong/text()').extract()[0]
            ext_name = ' '.join(hxs.select('//h1[@class="skuHeading"]/text()').extract()).strip()
            category = hxs.select('//div[@class="breadcrumb"]/nav/p/a/text()').extract()[-1]
            image_url = hxs.select('//img[@class="productImageLarge"]/@src').extract()
            if image_url:
                image_url = urljoin_rfc(base_url, image_url[0])
            brand = hxs.select('//img[@class="brandImageMedium"]/@alt').extract()
            brand = brand[0].replace(' logo', '') if brand else ''

            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('category', category)
            product_name = name + ext_name

            brand_in_name = False
            for w in re.findall('([a-zA-Z]+)', product_name):
                if w.upper() in brand.upper():
                    brand_in_name = True

            if brand.upper() not in product_name.upper() and not brand_in_name:
                product_name = brand + ' ' + product_name

            product_loader.add_value('name', product_name)
            product_loader.add_value('url', response.url)
            product_loader.add_value('identifier', product_id)

            product_loader.add_value('brand', brand)
            product_loader.add_value('sku', sku)
            discontinued = hxs.select('//p[contains(@class, "stock")]/span[@class="discontinued"]')
            if discontinued:
                # Does not include discontinued items
                return
            stock = hxs.select('//span[@class="inStock"]/strong/text()').extract()
            add_button = hxs.select('//input[contains(@class, "ajaxBuyButton")]')
            if stock:
                product_loader.add_value('stock', extract_price(stock[0]))
            elif add_button:
                product_loader.add_value('stock', 1)
            else:
                product_loader.add_value('stock', 0)
            price = hxs.select('//strong[@id="price_"]/text()').extract()[0]
            price = extract_price(price)
            if price < 50:
                product_loader.add_value('shipping_cost', 4.50)
            else:
                product_loader.add_value('shipping_cost', 0)

            product_loader.add_value('price', price)
            product_loader.add_value('image_url', image_url)
            yield product_loader.load_item()


