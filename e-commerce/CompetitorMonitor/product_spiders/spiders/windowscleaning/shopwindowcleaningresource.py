import re
import json
from decimal import Decimal, ROUND_UP
from copy import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product
from productloader import WindowsCleaningProductLoader


class ShopWindowCleaningResourceSpider(BaseSpider):
    name = 'shopwindowcleaningresource.com'
    start_urls = ('http://www.shopwindowcleaningresource.com',)

    def parse(self, response):
        # categories

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        category_urls = hxs.select('//div[contains(@class, "col-left") and contains(@class, "sidebar")]//div[contains(@class, "nav-container")]//li[not(ul)]/a/@href').extract()
        for url in category_urls:
            yield Request(urljoin_rfc(base_url, url))

        # next page
        next_page = hxs.select('//a[@class="next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        # products
        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)


    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        # sub products
        hxs = HtmlXPathSelector(response)

        # compound product
        identifier = hxs.select('//input[@type="hidden" and @name="product"]/@value')[0].extract()
        image_url = hxs.select('//div[@class="onsale-product-container"]/a/img/@src').extract()
        if not image_url:
            image_url = hxs.select('//p[@class="product-image"]/a[@id="zoom1"]/@href').extract()
        category = hxs.select('//div[@class="breadcrumbs"]//a/text()').extract()
        loader = WindowsCleaningProductLoader(item=Product(), selector=hxs)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        if category:
            loader.add_value('category', category[-1])

        sub_products = hxs.select('//table[@id="super-product-table"]//tr')[1:]
        if sub_products:
            item = loader.load_item()
            sub_products.sort(key=lambda p: p.select('td[1]//text()')[0].extract())
            i = 0
            for p in sub_products:
                name = p.select('td[1]//text()')[0].extract()
                price = ''.join(p.select('td[2]//text()').extract()).strip()
                in_stock = p.select('td[3]/input')
                loader = WindowsCleaningProductLoader(item=item, selector=hxs)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                loader.add_value('price', price)
                loader.add_value('sku', '')
                loader.add_value('identifier', '%s.%s' % (identifier, i))
                if not in_stock:
                    loader.add_value('stock', 0)
                yield loader.load_item()
                i += 1
            return

        name = hxs.select('//div[@class="product-name"]/h1/text()')[0].extract()
        loader.add_value('url', response.url)
        loader.add_value('sku', '')
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        out_of_stock = hxs.select('//p[contains(@class, "availability") and contains(@class, "out-of-stock")]')
        if out_of_stock:
            loader.add_value('stock', 0)
        price = hxs.select('//div[@class="product-shop"]//p[@class="special-price"]/span[2]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="product-shop"]//span[@class="regular-price"]/span/text()').extract()
        price = price if price else '0.00'
        loader.add_value('price', price)
        # TODO stock
        options = re.search('var spConfig = new Product\.Config\(({.*})\);', response.body)
        if options:
            item = loader.load_item()
            options = json.loads(options.group(1))
            base_price = float(options['basePrice'])
            for attribute in options['attributes'].values():
                for option in attribute['options']:
                    opt_item = Product(item)
                    opt_item['identifier'] += '.%s.%s' % (attribute['id'], option['id'])
                    opt_item['name'] += ' %s' % option['label']
                    opt_item['price'] = Decimal(str(float(base_price) + float(option['price'])))
                    yield opt_item
        else:
            yield loader.load_item()
