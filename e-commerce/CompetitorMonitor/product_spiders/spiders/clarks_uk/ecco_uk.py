# -*- coding: utf-8 -*-
import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request


from urlparse import urljoin


class EccoUkSpider(BaseSpider):

    name = "ecco_uk"
    start_urls = ["http://shopeu.ecco.com/uk/en/womens/view-all?page=1",
                  "http://shopeu.ecco.com/uk/en/mens/view-all?page=1",
                  "http://shopeu.ecco.com/uk/en/bags/view-all?page=1",
                  "http://shopeu.ecco.com/uk/en/girls-shoes",
                  "http://shopeu.ecco.com/uk/en/boysshoes",
                  "http://shopeu.ecco.com/uk/en/baby-shoes",
                  "http://shopeu.ecco.com/uk/en/kids-shoes/accessories"]

    base_url = "http://shopeu.ecco.com"
    download_delay = 1


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        subcategories = hxs.select("//div[@class='category-navigation']//a[not(contains(@href,'view-all'))]")

        category = None
        ignore_kids_subcategories = False
        ignore_mw_subcategories = False

        if 'girls-shoes' in response.url:
            category = 'Kids Girls'
        if 'boysshoes' in response.url:
            category = 'Boys Shoes'
        if 'baby-shoes' in response.url:
            category = 'Kids Toddlers'
        if 'kids-shoes/accessories' in response.url:
            category = 'Kids Accessories'
        if category:
            ignore_kids_subcategories = True

        if 'mens' in response.url in response.url:
            ignore_mw_subcategories = True

        for subcategory in subcategories:
            subcategory_url = urljoin(response.url, subcategory.select("./@href").extract()[0]) + '?page=1'
            subcategory_name = subcategory.select("./text()").extract()[0]

            if ignore_kids_subcategories:
                if subcategory_name.strip().lower() in [
                    "view all",
                    "new arrivals",
                    "best sellers",
                    "bestsellers"
                    "seasonal offers"]:
                    continue
            if ignore_mw_subcategories:
                if subcategory_name.strip().lower() in [
                    "view all",
                    "new arrivals",
                    "bestsellers",
                    "casual",
                    "formal",
                    "sport",
                    "seasonal offers",
                    "classic",
                    "classics",
                    "touch collection",
                    "sculptured",
                    "trends"]:
                    continue

            meta = {'subcategory': subcategory_name, 'category': category}
            yield Request(subcategory_url, meta=meta, callback=self.parse_subcategory)


    def parse_subcategory(self, response):
        data = re.findall('Listing.html = (.*);', response.body)
        if not data:
            return

        products_html = json.loads(data[0])['products']
        hxs = HtmlXPathSelector(text=products_html)

        items = hxs.select("//a[@class='item-link']")
        for item in items:
            l = {}
            l['name'] = item.select(".//h3[@class='item-name']/text()").extract()[0]
            l['url'] = self.base_url + item.select("./@href").extract()[0]
            l['stock'] = 0
            l['brand'] = 'Ecco'

            meta = {'l': l,
                    'subcategory': response.meta['subcategory'],
                    'category': response.meta['category']}

            yield Request(url=l['url'], meta=meta, callback=self.parse_item)

        # There is a bug, sometimes pagination links not showing up so we have to manually go to the next page
        if items:
            current_page = re.findall(re.compile('page=(\d+)'), response.url)[0]
            next_page = str(int(current_page) + 1)
            next_page = response.url.replace('page='+current_page, 'page='+next_page)
            meta = {'subcategory': response.meta['subcategory'],
                    'category': response.meta['category']}

            yield Request(next_page, meta=meta, callback=self.parse_subcategory)


    def parse_item(self, response):
        hxs  = HtmlXPathSelector(response)
        item = response.meta['l']

        category = response.meta['category']

        if not category:
            category = hxs.select("//div[@itemprop='breadcrumb']/a[@class='cat']/text()").extract()[0].strip()
            category = 'Accessories' if category.lower() == 'bags' else category.title()

        categories = [category, response.meta['subcategory']]

        options = hxs.select("//div[@class='bx-color']/ul/li")
        option_main_part = hxs.select("//meta[@itemprop='productID']/@content").extract()[0].split('-')[0].replace('sku:', '').strip()
        constant_name = item['name']

        for option in options:

            option_postfix = option.select("./@opt-style_key").extract()[0]
            option_name = option.select("./@title").extract()[0]
            item['name'] = constant_name + ' ' + option_name
            item['image_url'] = hxs.select(".//img/@src").extract()[0]
            try:
                item['price'] = hxs.select("//div[@class='bx-nameprice clr']/div[contains(@class,{})]/div/text()".format(option_postfix)).extract()[0].strip()
            except:
                continue
            if  item['price']:
                item['price'] = re.findall(re.compile('(\d+.\d*.\d*)'), item['price'])[0]
                item['stock'] = 1
                item['shipping'] = '2.95' if float(item['price']) < 49 else 0

            item['sku'] = option_main_part + '-' + option_postfix
            item['identifier'] = item['sku']

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

            for category in categories:
                l.add_value('category', category)

            yield l.load_item()
