from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
import re

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class LeganieSpider(LegoMetadataBaseSpider):
    name = u'leganie.cz'
    allowed_domains = ['www.leganie.cz']
    start_urls = [
        u'http://www.leganie.cz',
    ]
    errors = []
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//td[@id="workspace"]/table/tr/td[@class="uvod_tab"]/a/@href').extract()
        for url in items:
            yield Request(urljoin(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//div[@class="zbozi"]/div[@class="nazev"]/div/a/@href').extract()
        next_page = hxs.select(u'//div[@id="strankovani"]/a/font[contains(text(), "\xbb")]/../@href').extract()
        for url in items:
            yield Request(urljoin(base_url, url.replace('&', '')), callback=self.parse_product)
        if next_page:
            yield Request(urljoin(base_url, next_page.pop()), callback=self.parse_category)

    def parse_price(self, price):
        try:
            price, count = re.subn(r'[^0-9 .,]*([0-9 .,]+)\W*K.*', r'\1', price.strip())
        except TypeError:
            return False
        if count:
            price = price.replace(",", ".").replace(" ", "")
            try:
                price = float(price)
            except ValueError:
                return False
            else:
                return price
        elif price.isdigit():
            return float(price)
        return False

    def get_sku_from_text(self, text):
        try:
            id, count = re.subn(r'[^0-9]*([0-9]{4,6}).*', r'\1', text)
        except TypeError:
            return ""
        if count:
            id = id.strip()
            try:
                int(id)
            except ValueError:
                return ""
            else:
                return id
        return False

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//td[@id="workspace"]/h1/a/text()').pop().extract().strip()

        category = hxs.select('//div[@class="odkazy_cesta"]/a/text()').pop().extract().strip()

        sku = hxs.select('//input[@name="detail"]/@value').extract().pop()

        pid = sku

        if not sku:
            sku = pid

        price = self.parse_price(hxs.select('//table[@id="detail_tabulka2"]/tr/th[contains(text(), "Cena s DPH")]/following-sibling::td/descendant-or-self::text()').pop().extract())

        stock = hxs.select('//table[@id="detail_tabulka2"]/tr/td//img[contains(@src, "skladem.png")]')

        if price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin(base_url, response.url))
            loader.add_value('name', name)
            try:
                loader.add_xpath('image_url', '//td[@id="detail_foto"]/div/a/img/@src', Compose(lambda v: urljoin(base_url, v[0])))
            except IndexError:
                self.errors.append("No image set for url: '%s'" % urljoin(base_url, response.url))
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('identifier', pid)
            loader.add_value('brand', 'LEGO')
            loader.add_value('shipping_cost', 69)
            if not stock:
                loader.add_value('stock', 0)
            yield self.load_item_with_metadata(loader.load_item())
        else:
            self.errors.append("No price set for url: '%s'" % urljoin(base_url, response.url))
