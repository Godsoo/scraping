import os
from copy import deepcopy
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class NeimanmarcusSpider(BaseSpider):
    name = 'stylebop-neimanmarcus.com'
    allowed_domains = ['neimanmarcus.com']
    start_urls = ['http://www.neimanmarcus.com/index.jsp']

    ids = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//a[@class="silo-link" and not(contains(text(), "Designers")) and not(contains(text(), "MyNM"))]/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@class="category-menu"]//a[not(contains(@href, "Designers"))]/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_category)

        # categories = hxs.select('//li[contains(h2/text(), "Categories")]/ul/li/div/a/@href').extract()
        # sub_categories = hxs.select('//li/ul/li/div/a/@href').extract()
        # sub_categories += hxs.select('//div[contains(@class, "category")]/a/@href').extract()
        # for sub_category in sub_categories:
        #     yield Request(urljoin_rfc(base_url, sub_category), callback=self.parse_category)

        products = hxs.select('//div[contains(@class, "productname")]/a/@href').extract()
        if products:
            yield Request(response.url, dont_filter=True, callback=self.parse_products)

    def parse_products(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category = ''.join(hxs.select('//a[@class="catalognavOpenItem active" and @id="rootcatnav"]/text()').extract()).strip()

        final_url = '?page=1&pageSize=%s&sort=PCS_SORT&definitionPath=/nm/commerce/pagedef/template/EndecaDrivenHome&allStoresInput=false'

        total_items = int(hxs.select('//span[@id="numItems"]/text()').extract()[0])
        if total_items > 30 and 'pageSize' not in response.url:
            final_url = response.url + final_url
            yield Request(final_url % (total_items), callback=self.parse_products, meta={'category': category})

        products = hxs.select('//div[contains(@class, "productname")]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product.split('?')[0]), callback=self.parse_product, meta={'category': category})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        l = ProductLoader(item=Product(), response=response)
        identifier = hxs.select('//input[@name="itemId"]/@value').extract()[0]
        l.add_value('identifier', identifier)

        sku = hxs.select('//span[@id="MpsShortSku"]/text()').re('#(\w+).')
        sku = sku[0] if sku else ''
        l.add_value('sku', sku)

        brand = hxs.select('//span[@class="product-designer"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        l.add_value('brand', brand)

        name = ''.join(hxs.select('//h1[@itemprop="name"]/text()').extract()).strip()
        l.add_value('name', name)

        l.add_value('url', response.url)

        image_url = hxs.select('//div[@class="img-wrap"]/img/@src').extract()
        if image_url:
            l.add_value('image_url', image_url[0])
        l.add_value('category', response.meta.get('category', ''))

        price = hxs.select('//div[@class="price pos1priceDisplayStyleOverride"]/text()').extract()
        if price:
            price = price[0]
        else:
            price = hxs.select('//p[@itemprop="price"]/text()').extract()
            if price:
                price = price[0]
            else:
                price = hxs.select('//span[@itemprop="price"]/text()').extract()
                if price:
                    price = price[0]

        if not price:
            price = 0

        l.add_value('price', price)

        out_of_stock = hxs.select('//div[@class="cannotorder"]')
        if out_of_stock:
            l.add_value('stock', 0)

        base_item = l.load_item()
        sub_items = hxs.select('//div[@class="lineItem"]')
        if sub_items:
            for sub_item in sub_items:
                item = deepcopy(base_item)
                price = sub_item.select('.//div[@class="price pos1priceDisplayStyleOverride"]/text()').extract()
                if price:
                    price = price[0]
                else:
                    price = sub_item.select('.//p[@itemprop="price"]/text()').extract()
                    if price:
                        price = price[0]
                    else:
                        price = sub_item.select('.//span[@itemprop="price"]/text()').extract()
                        if price:
                            price = price[0]

                if not price:
                    price = '0'

                item['price'] = extract_price(price)
                item['name'] = sub_item.select('.//h6/text()').extract()[-1].strip()
                sku = hxs.select('.//span[@id="MpsShortSku"]/text()').re('#(\w+).')
                item['sku'] = sku[0] if sku else ''

                identifier = sub_item.select('.//div/input[contains(@id, "prod")]/@value').extract()
                if not identifier:
                    continue
                item['identifier'] = item['identifier'] + '-' + identifier[0]
                if item['identifier'] not in self.ids:
                    self.ids.append(item['identifier'])
                    yield item
                else:
                    continue
        else:
            if base_item['identifier'] not in self.ids:
                self.ids.append(base_item['identifier'])
                yield base_item
            else:
                return
