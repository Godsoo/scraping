# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, time

from product_spiders.utils import extract_price_eu as extract_price

class DuneDeSpider(BaseSpider):

    name = "dune_de"
    start_urls = ['http://www.dunelondon.com/de-de/']

    categories = ["http://www.dunelondon.com/de-de/Damenstiefel-Mit-hohem-Absatz-Kn%C3%B6chelhoch-waden-und-kniehoch/19ain/",
                  "http://www.dunelondon.com/de-de/Damenschuhe-Absatzschuhe-Schuhe-mit-Keilabsatz-Flache-Schuhe-Sandalen-und-Pumps/199c4/",
                  "http://www.dunelondon.com/de-de/eu/ladies-sandals-dept3001/",
                  "http://www.dunelondon.com/de-de/Damenhandtaschen-Tag-Clutch-Abend-und-elegante-Taschen/199mj/",
                  "http://www.dunelondon.com/de-de/Accessoires-f%C3%BCr-Damen-Portemonnaies-Schmuck-G%C3%BCrtel-und-H%C3%BCte/19ame/",
                  "http://www.dunelondon.com/de-de/Herrenstiefel-f%C3%BCr-Freizeit-und-B%C3%BCro/19azo/",
                  "http://www.dunelondon.com/de-de/Herrenschuhe-L%C3%A4ssige-und-formelle-Styles/19bdw/",
                  "http://www.dunelondon.com/de-de/eu/mens-sandals-dept3601/",
                  "http://www.dunelondon.com/de-de/Accessoires-f%C3%BCr-Herren-Taschen-Sonnenbrillen-Handschuhe-H%C3%BCte-Schals/19bfs/"]

    def parse(self, response):
        for url in self.categories:
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):

        hxs   = HtmlXPathSelector(response)
        pages = hxs.select("//ul[@class='paginate']/li/a/@href").extract()

        for page in pages:
            yield Request(url=page, callback=self.parse_category)

        items = hxs.select("//div[@id='productDataOnPage']//ul")
        for item in items:

            l = {}

            l['name'] = item.select(".//h3//span[@class='bcase']/text()").extract()[0]
            l['url'] = item.select(".//h3//a/@href").extract()[0]

            try:
                l['price'] = item.select(".//li[contains(@id,'listing_price')]/span[@class='mainPriceOnSale']/text()").extract()[0]
            except:
                l['price'] = item.select(".//li[contains(@id,'listing_price')]/text()").extract()[0]

            l['stock'] = 0
            l['brand'] = 'Ecco'

            yield Request(url=l['url'], meta={'l': l}, callback=self.parse_item)

    def parse_item(self, response):

        hxs  = HtmlXPathSelector(response)
        item = response.meta['l']

        all_data = hxs.select("//script[contains(text(),'sku')]/text()").extract()[0]

        item['brand'] = re.findall(re.compile('\"brand\": \"(.*?)\"'), all_data)[0]
        item['sku'] = re.findall(re.compile('\"id\": \"(.*?)\"'), all_data)[0]
        item['category'] = re.findall(re.compile('\"category\": \"(.*?)\"'), all_data)[0]
        item['category'] = re.findall(re.compile('\"category\": \"(.*?)\"'), all_data)[0]
        item['category'] = 'Accessories' if item['category'].lower() == 'taschen' else item['category']

        item['image_url'] = hxs.select("//meta[@property='og:image']/@content").extract()[0]

        if  item['price']:
            item['price'] = re.findall(re.compile('(\d+.\d*.\d*)'), item['price'])[0]
            item['shipping'] = '4.00'

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
        l.add_value('price', extract_price(item['price']))
        l.add_value('stock', item['stock'])
        l.add_value('brand', item['brand'])
        l.add_value('identifier', item['identifier'])
        l.add_value('sku', item['sku'])
        l.add_value('shipping_cost', item['shipping'])
        l.add_value('category', item['category'])

        yield l.load_item()
