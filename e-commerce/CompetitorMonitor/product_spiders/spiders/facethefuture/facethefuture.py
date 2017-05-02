import logging
import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader


class FaceTheFutureSpider(BaseSpider):
    name = "facethefuture-facethefuture"
    allowed_domains = ["www.facethefuture.co.uk"]
    start_urls = (
        "http://www.facethefuture.co.uk/shop/shop-by-brand/",
    )
    errors = []

    products_parsed = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        brands = hxs.select('//div[@id="subcategories"]/ul/li/h5/a/@href').extract()
        for url in brands:
            yield Request(url, callback=self.parse_listing)

    def parse_listing(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sub_categories = hxs.select('//a[@class="subcategory-name"]/@href').extract()
        for sub_category in sub_categories:
            yield Request(urljoin_rfc(base_url, sub_category), callback=self.parse_listing)
            
        links = hxs.select('//ul[contains(@class, "product_list")]/li/div/div[2]/h5/a/@href').extract()
        for link in links:
            yield Request(link, callback=self.parse_product)

        next_page = hxs.select('//ul[@class="pagination"]/li[@id="pagination_next_bottom"]/a/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page.pop()), callback=self.parse_listing)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h1[@itemprop="name"]/text()').extract().pop()

        identifier = hxs.select('//input[@name="id_product"]/@value').extract().pop()
        sku = hxs.select('//span[@itemprop="sku"]/text()').extract()
        if not sku:
            sku = re.search("productReference='(.*?)\';", response.body)
            sku = sku.group(1).lower() if sku else ''
        else:
            sku = sku.pop().lower()

        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        if not price:
            price = '0.0'
        stock = hxs.select('//span[@id="availability_value"]/text()').extract()
        if stock and 'is no longer in stock' in stock.pop().lower():
            stock = 0
        else:
            stock = 1
        category = hxs.select('//div[contains(@class, "breadcrumb")]/a/text()').extract().pop()
        brand = hxs.select('//div[contains(@class, "breadcrumb")]/a/text()').extract()[1]
        image_url = hxs.select('//div[@id="image-block"]//img/@src').extract()

        if 'clearance' in name.lower():
            self.log('Skip product %s <%s>' % (name, response.url))
            return
        loader = ProductLoader(response=response, item=Product())
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier)
        if sku:
            loader.add_value('sku', sku)
        if stock:
            loader.add_value('stock', '1')
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url.pop()))
        if category:
            loader.add_value('category', category)
        if 'CLEARANCE' not in brand:
            loader.add_value('brand', brand)
        else:
            loader.add_value('category', "Clearance products")
        loader.add_value('shipping_cost', 'N/A')

        item = loader.load_item()

        yield item

        combinations = ''
        for l in response.body.split('\n'):
            if 'var combinations = ' in l:
                combinations = l

        if combinations:
            combinations = combinations.replace('var combinations = ', '').strip()[:-1]
            data = json.loads(combinations)

            image_to_replace = ''
            if item['image_url']:
                try:
                    image_to_replace = re.search(r'(/\d+-large_default/)', item['image_url']).group(1)
                except Exception, e:
                    print e

            for opt_id, opt_obj in data.items():
                opt_item = Product(item)
                opt_item['identifier'] = opt_item['identifier'] + ':' + str(opt_id)
                opt_item['name'] += ' - ' + opt_obj['attributes_values'].items()[0][1]
                if image_to_replace:
                    opt_item['image_url'] = opt_item['image_url'].replace(image_to_replace, '/%s-large_default/' % opt_obj['id_image'])
                if 'clearance' in opt_item['name'].lower():
                    self.log('Skip product %s <%s>' % (name, response.url))
                    continue
                yield opt_item
