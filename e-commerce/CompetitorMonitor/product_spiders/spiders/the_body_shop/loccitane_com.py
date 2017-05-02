# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import re
import json


class LoccitaneSpider(BaseSpider):
    name = u'thebodyshop-loccitane.com'
    allowed_domains = ['loccitane.com']
    start_urls = [
        'http://uk.loccitane.com/shea-butter-organic-certified,83,1,29776,270132.htm?newversion=true&=',
        "http://uk.loccitane.com/l'occitane-shea-butter-hand-cream,83,1,29776,271739.htm?newversion=true&=",
        'http://uk.loccitane.com/verveine-shower-gel--verbena-,83,1,29793,269711.htm?newversion=true&=',
        'http://uk.loccitane.com/cherry-blossom-eau-de-toilette,83,1,29831,270200.htm?newversion=true&=',
        'http://uk.loccitane.com/verbena-eau-de-toilette,83,1,29793,269708.htm?newversion=true&=',
        'http://uk.loccitane.com/shea-delightful-rose-lip-balm,83,1,29776,626404.htm?newversion=true&=',
        'http://uk.loccitane.com/precious-bb-cream-spf-30-fair-shade,83,1,29786,686278.htm?newversion=true&=',
        'http://uk.loccitane.com/shea-light-comforting-cream,83,1,29776,649980.htm?newversion=true&=',
        'http://uk.loccitane.com/immortelle-precious-serum,83,1,29786,292398.htm?newversion=true&=',
        'http://uk.loccitane.com/complete-care-moisturiser,83,1,29810,272614.htm?newversion=true&='
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        category = hxs.select('//*[@id="breadcrumb"]//a/span/text()').extract()[1:]
        brand = hxs.select('//*[@id="product_ingredients"]//div[@class="content_container"]//a[contains(text(), "View all")]/b/text()').extract()
        brand = brand[0] if brand else ''

        match = re.search(r"ko.observableArray\((.*?)\);", response.body, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if match:
            result = match.group(1)
            data = json.loads(result)
            for item in data:
                if len(data) > 1:
                    if '150 ml' not in item['size']:
                        continue
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', item['productId'])
                product_loader.add_value('name', item['title'] + ' ' + item['size'])
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                product_loader.add_value('sku', item['sku'])
                price = extract_price(item['price'])
                product_loader.add_value('price', price)
                product_loader.add_value('url', response.url)
                product_loader.add_value('category', category)
                product_loader.add_value('brand', brand)
                if price < 30:
                    product_loader.add_value('shipping_cost', 3.95)
                product = product_loader.load_item()
                yield product
