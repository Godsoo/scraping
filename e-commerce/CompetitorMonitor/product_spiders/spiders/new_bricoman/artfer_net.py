# -*- coding: utf-8 -*-
import csv
import os.path
import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class ArtFerSpider(BaseSpider):
    name = 'newbricoman-artfer.net'
    allowed_domains = ('artfer.net', )
    start_urls = ('http://www.artfer.net/shop/catalog/seo_sitemap/category/', )

    def __init__(self, *args, **kwargs):
        super(ArtFerSpider, self).__init__(*args, **kwargs)

        self.rows = []

        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.rows.append(row)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        pages = hxs.select("//div[@class='pages']/ol/li/a/@href").extract()
        for page_url in pages:
            url = urljoin_rfc(get_base_url(response), page_url)

            r = Request(url, callback=self.parse)
            yield r

        categories = hxs.select("//ul[@class='bare-list']/li/a/@href").extract()

        for category_url in categories:
            url = urljoin_rfc(get_base_url(response), category_url)

            r = Request(url, callback=self.parse_products_list)
            yield r

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)

        pages = hxs.select("//div[@class='pages']//li/a/@href").extract()
        for page_url in pages:
            url = urljoin_rfc(get_base_url(response), page_url)

            r = Request(url, callback=self.parse_products_list)
            yield r

        category = hxs.select("//ul[@class='breadcrumbs']/li[last()]/strong/text()").extract()[0]

        try:
            products = hxs.select("//div[contains(@class, 'catalog-listing')]/div[contains(@class, 'listing-item')]")
            for p in products:
                name = p.select("div/h3/a/text()").extract()[0]
                if "SUPER OFFERTA" in name:
                    name = name.replace("SUPER OFFERTA", "")
                if "-" in name:
                    parts = name.split("-")
                    brand = parts[0].strip()
                    name = "".join(parts[1:]).strip()
                else:
                    brand = ""

                url = p.select("div/h3/a/@href").extract()[0]
                if not brand:
                    brand = p.select(".//div[@class='description']/strong/text()").extract()
                    if brand:
                        brand = brand[0].strip()
                    else:
                        brand = ""
                image_url = p.select("div[@class='product-image']/a/img/@src").extract()[0]
                image_url = urljoin_rfc(get_base_url(response), image_url)
                sku = p.select(".//p[@class='custom-product-sku']/text()").re(r'.*:(.*)')[0].strip()
                if p.select(".//div[@class='out-of-stock']"):
                    stock = 0
                else:
                    stock = None
                price_el = p.select("div[@class='product-shop']/div[@class='price-box']/span[@class='special-price']/span[@class='price']")
                if price_el:
                    identifier = price_el.select("@id").re(r'product-price-(.*)')[0]
                    price = price_el.select("text()").extract()[0].strip()
                else:
                    price_el = p.select("div[@class='product-shop']/div[@class='price-box']/span[@class='regular-price']")
                    identifier = price_el.select("@id").re(r'product-price-(.*)')[0]
                    price = price_el.select("./span/text()").extract()[0].strip()
                price = price.replace(".", "").replace(",", ".")

                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', name)
                loader.add_value('url', url)
                loader.add_value('category', category)
                loader.add_value('brand', brand)
                loader.add_value('image_url', image_url)
                loader.add_value('sku', sku)
                loader.add_value('identifier', identifier)
                loader.add_value('stock', stock)
                loader.add_value('price', price)

                yield loader.load_item()

            products2 = hxs.select("//div[contains(@class, 'catalog-listing')]//li[@class='item']")
            for p in products2:
                name = p.select("h3/a/text()").extract()[0]
                if "SUPER OFFERTA" in name:
                    name = name.replace("SUPER OFFERTA", "")
                if "-" in name:
                    parts = name.split("-")
                    brand = parts[0].strip()
                    name = "".join(parts[1:]).strip()
                else:
                    brand = ""

                url = p.select("h3/a/@href").extract()[0]
                if not brand:
                    brand = p.select(".//div[@class='description']/strong/text()").extract()
                    if brand:
                        brand = brand[0].strip()
                    else:
                        brand = ""
                image_url = p.select("div[@class='product-image']/a/img/@src").extract()[0]
                image_url = urljoin_rfc(get_base_url(response), image_url)
                sku = p.select(".//p[@class='custom-product-sku']/text()").re(r'.*:(.*)')[0].strip()
                if p.select(".//div[@class='out-of-stock']"):
                    stock = 0
                else:
                    stock = None
                price_el = p.select("div[@class='price-box']/span[@class='special-price']/span[@class='price']")
                if price_el:
                    identifier = price_el.select("@id").re(r'product-price-(.*)')[0]
                    price = price_el.select("text()").extract()[0].strip()
                else:
                    price_el = p.select("div[@class='price-box']/span[@class='regular-price']")
                    identifier = price_el.select("@id").re(r'product-price-(.*)')[0]
                    price = price_el.select("./span/text()").extract()[0].strip()
                price = price.replace(".", "").replace(",", ".")

                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', name)
                loader.add_value('url', url)
                loader.add_value('category', category)
                loader.add_value('brand', brand)
                loader.add_value('image_url', image_url)
                loader.add_value('sku', sku)
                loader.add_value('identifier', identifier)
                loader.add_value('stock', stock)
                loader.add_value('price', price)

                yield loader.load_item()
        except IndexError:
            r = Request(url, callback=self.parse_products_list, dont_filter=True)
            yield r

        if not products and not products2:
            logging.error("ASD. No products: %s" % response.url)

