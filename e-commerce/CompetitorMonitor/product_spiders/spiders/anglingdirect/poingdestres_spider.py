# -*- encoding: utf-8 -*-
from decimal import Decimal
import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import FormRequest

class climaxtackle_spider(BaseSpider):
    name = 'poingdestres.co.uk'
    allowed_domains = ['poingdestres.co.uk', 'www.poingdestres.co.uk']
    start_urls = ('http://www.poingdestres.co.uk',)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        image_url = hxs.select('//p[contains(@class, "product-image")]/a/@href').extract()
        price = extract_price("".join(hxs.select('//div/span/span[@class="price"]/text()').extract()).strip())
        if not price:
            price = extract_price("".join(hxs.select('//p[@class="special-price"]//span[@class="price"]/text()').extract()).strip())
        if image_url:
            image_url = image_url[0]  # urljoin_rfc(get_base_url(response), image_url[0])
        category = hxs.select('//div[contains(@class, "breadcrumbs")]/ul/li/a/text()').extract()
# hxs.select(u'//div[@id="Breadcrumb"]//a/text()').extract()
        category = category[-1] if category else ''
        options = hxs.select('//select/option[@value!=""]')
        identifier = hxs.select('//input[@name="product" and @value!=""]/@value').extract()[0]  # re.search(u'poingdestres\.co\.uk/(.*)/', response.url).group(1)
        name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0]
        brand = ''.join(hxs.select('//div[contains(@class, "brand-name")]/text()').extract()).strip()
        if options:
            # options
            url = response.url
            for option in options:
                try:
                    name2 = option.select('text()').extract()[0].split(u' +£')[0]
                except:
                    name2 = ''
                option_price = extract_price(option.select('@price').extract()[0])
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('url', url)
                loader.add_value('name', brand + u' ' + name + u' ' + name2)
                loader.add_value('price', price + option_price)
                loader.add_value('identifier', identifier + '.%s' % option.select('@value').extract()[0])
                loader.add_value('category', category)
                loader.add_value('brand', brand)
                if image_url:
                    loader.add_value('image_url', image_url)
                yield loader.load_item()
        elif re.search('Product.Config\((.*)\);', response.body):
            options = re.search('Product.Config\((.*)\);', response.body)
            options = json.loads(options.group(1))
            url = response.url
            for attribute in options['attributes'].values():
                for i, option in enumerate(attribute['options'], 1):
                    name2 = option['label']
                    option_price = Decimal(option['price'])
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('url', url)
                    loader.add_value('name', brand + u' ' + name + u' ' + name2)
                    loader.add_value('price', price + option_price)
                    loader.add_value('identifier', identifier + '.%s' % option['products'][0])
                    loader.add_value('category', category)
                    loader.add_value('brand', brand)
                    if image_url:
                        loader.add_value('image_url', image_url)
                    yield loader.load_item()

        else:
            # hxs.select("//div[@class='ProductDetails']/h1/text()")[0].extract().strip()
            url = response.url
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', url)
            loader.add_value('name', brand + ' ' + name)
            loader.add_value('price', price)
            loader.add_value('identifier', identifier)
            loader.add_value('category', category)
            loader.add_value('brand', brand)
            if image_url:
                loader.add_value('image_url', image_url)
            yield loader.load_item()


    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)

        # categories
        hxs = HtmlXPathSelector(response)
        categories_urls = hxs.select('//li[contains(@class, "level0")]/a/@href').extract()  # hxs.select('//div[@id="navigation"]/div/h2/a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url))

        # subcats
        subcats_urls = hxs.select('//div[@class="block-content"]/ul/li/a/@href').extract()  # hxs.select('//div[@id="navigation"]/div/div/a/@href').extract()
        for surl in subcats_urls:
            yield Request(urljoin_rfc(base_url, surl))

        # pages
        # pages_urls = hxs.select('//span[@id="Pagination"]/a/@href').extract()
        # for page in pages_urls:
        next = hxs.select('//li[@class="next"]/a/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]))

        products = hxs.select('//h2/a/@href').extract()  # hxs.select('//div[@class="listitem"]')
        # products += hxs.select('//div[@class="altlistitem"]')
        for p in products:
            url_product = p  # .select('.//div[@class="heading"]/a/@href')[0].extract()
            yield Request(urljoin_rfc(base_url, url_product), callback=self.parse_product)
