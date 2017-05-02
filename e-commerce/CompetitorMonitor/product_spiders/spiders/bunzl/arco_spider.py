import re
import os
import json
import demjson

from scrapy import Spider, Request

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class ArcoSpider(Spider):
    name = 'bunzl-arco.co.uk'
    allowed_domains = ['arco.co.uk']

    start_urls = ('http://www.arco.co.uk', )

    def parse(self, response):
        categories = response.xpath('//ul[@id="megamenu"]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = response.xpath('//div[@class="result"]/div/a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product2)

        next = response.xpath('//a[span[@class="icon-arrow-right"]]/@href').extract()
        if next:
            yield Request(response.urljoin(next[0]))

    def parse_product2(self, response):

        image_url = response.xpath(u'//div[@id="imageholder"]//img[@name="lpic"]/@src')
        if not image_url:
            image_url = response.xpath("//div[@id='productImage']/img/@src")
        if image_url:
            image_url = image_url[0].extract()
            image_url = response.urljoin(image_url)
        else:
            image_url = ''

        options = response.xpath(u'//table[@class="producttbl"]//tr[not(child::th)]')
        for option in options:
            if not option.xpath(u'./td[2]/span[@class="linedesc"]'):
                continue
            sku = option.xpath(u'./td[1]/text()')[0].extract().strip()
            brand = response.xpath('//img/@alt').re('(.*) brand logo')
            name = option.xpath('.//span[@class="linedesc"]/text()').extract()
            name = name[0].strip() if name else ''
            price = option.xpath(u'./td[4]/div/text()')[0].extract()

            categories = response.xpath('//div[@id="bcrumb"]/p//text()').extract()[1:-1]
            categories = map(lambda x: x.replace('>', '').strip(), categories)
            categories = [category for category in categories if category != ""]

            out_of_stock = option.xpath('.//span[@class="stock-o"]').extract()

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('category', categories)
            loader.add_value('name', name)
            loader.add_value('brand', brand)
            loader.add_value('url', response.url)
            loader.add_value('price', price)
            loader.add_value('image_url', image_url)
            loader.add_value('sku', sku)
            loader.add_value('identifier', sku)
            if out_of_stock:
                loader.add_value('stock', 0)

            yield loader.load_item()

        if not options:
            m = re.search('skus =\s*(\{[^;]*});', response.body, re.M)
            if m:
                options_js = m.group(1)
                options = demjson.decode(options_js)

                def parse(options, name=''):
                    if not isinstance(options, dict):
                        return None
                    if 'code' in options:
                        res = options.copy()
                        res['name'] = name
                        return res
                    res = []
                    for key, value in options.items():
                        name_part = name + ' ' + key
                        subres = parse(value, name_part)
                        if isinstance(subres, list):
                            res += subres
                        else:
                            res.append(subres)
                        return res

                name = response.xpath("//div[@id='productDesc']/h1/text()").extract()[0]

                products = parse(options, name=name)
                for p in products:
                    sku = p['code']

                    brand = ''
                    price = p['price']
                    categories = response.xpath('//ul[@class="crumbs"]//a/text()').extract()[1:]
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('category', categories)
                    loader.add_value('name', name)
                    loader.add_value('brand', brand)
                    loader.add_value('url', response.url)
                    loader.add_value('price', price)
                    loader.add_value('image_url', image_url)
                    loader.add_value('sku', sku)
                    loader.add_value('identifier', sku)
                    yield loader.load_item()
