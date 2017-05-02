# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request
import re
import json


class DuneUkSpider(BaseSpider):
    name = "dune_uk"
    start_urls = [
        "http://www.dunelondon.com/ladies-boots-dept3201/?page=1",
        "http://www.dunelondon.com/ladies-shoes-dept3101/?page=1",
        "http://www.dunelondon.com/ladies-sandals-dept3001/?page=1",
        "http://www.dunelondon.com/ladies-bags-dept3302/?page=1",
        "http://www.dunelondon.com/ladies-accessories-dept3301/?page=1",
        "http://www.dunelondon.com/mens-boots-dept3701/?page=1",
        "http://www.dunelondon.com/mens-shoes-dept3501/?page=1",
        "http://www.dunelondon.com/mens-sandals-dept3601/?page=1",
        "http://www.dunelondon.com/mens-accessories-dept3801/?page=1"
    ]

    data_regex = re.compile('dataLayer = (\[.*?\]);.*var ', re.DOTALL)

    def parse(self, response):

        hxs = HtmlXPathSelector(response)

        pages = hxs.select("//link[@rel='next']/@href").extract()
        for page in pages:
            yield Request(
                url=page,
                callback=self.parse,
            )

        # products
        items = hxs.select("//div[@id='productDataOnPage']//ul")

        for item in items:
            l = {
                'url': item.select(".//h3//a/@href").extract()[0],
                'stock': 0,
                'brand': 'Ecco'
            }

            yield Request(url=l['url'], meta={'l': l}, callback=self.parse_item, dont_filter=True)

    def parse_item(self, response):

        hxs = HtmlXPathSelector(response)
        item = response.meta['l']

        options = hxs.select("//div[@class='variantTableHolder']//ul[@class='prodswatch']/li[@class='swatchImg']")

        for option in options:
            url = option.select("./a/@href").extract()[0]
            yield Request(
                url=url,
                meta={'item': item},
                callback=self.parse_option
            )

        if not options:
            yield Request(
                url=response.url,
                meta={'item': item},
                callback=self.parse_option
            )

    def parse_option(self, response):

        hxs = HtmlXPathSelector(response)
        item = response.meta['item']

        all_data = hxs.select("//script[contains(text(),'sku')]/text()").extract()[0]

        data_text = ''.join(self.data_regex.findall(all_data))
        data_json = json.loads(data_text)

        item['name'] = hxs.select("//div[@class='productTITLE']//span[@class='prodName1']/text()").extract()[0]
        item['sku'] = data_json[0]['ecommerce']['detail']['products'][0]['size'][0]['sku']

        breadcrumbs = hxs.select("//div[@id='crumb']/span[position() > 1]//text()").extract()
        breadcrumbs = [x.strip() for x in breadcrumbs]
        category = "{brand} > {breadcrumbs}".format(
            brand=item['brand'],
            breadcrumbs=" ".join(breadcrumbs)
        ).strip()
        item['category'] = category

        brand = data_json[0]['ecommerce']['detail']['products'][0]['brand']
        brand = re.sub('mens', '', brand.lower())
        brand = re.sub('ladies', '', brand.lower())
        item['brand'] = brand.strip().upper()

        item['image_url'] = hxs.select("//meta[@property='og:image']/@content").extract()[0]
        item['price'] = hxs.select(".//span[@id='priceCopy']/text()").extract()[0]

        if item['price']:
            item['price'] = re.findall(re.compile('(\d+.\d*.\d*)'), item['price'])[0]
            item['shipping'] = '3.50'

        item['identifier'] = item['sku']

        options = hxs.select("//div[@class='variantTableHolder']//ul[@class='avail']//img/@id").extract()
        for option in options:
            if 'selectyes' in option:
                item['stock'] = 1
                break

        l = ProductLoader(item=Product(), response=response)

        l.add_value('name', item['name'])
        l.add_value('image_url', item['image_url'])
        l.add_value('url', item['url'])
        l.add_value('price', item['price'])
        l.add_value('stock', item['stock'])
        l.add_value('brand', item['brand'])
        l.add_value('identifier', item['identifier'])
        l.add_value('sku', item['sku'])
        l.add_value('shipping_cost', item['shipping'])
        l.add_value('category', item['category'])

        yield l.load_item()
