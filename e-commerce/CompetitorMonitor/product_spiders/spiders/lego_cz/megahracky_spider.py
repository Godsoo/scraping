from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import re

from utils import extract_price

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class MegaHrackySpider(LegoMetadataBaseSpider):
    name = u'megahracky.cz'
    allowed_domains = ['megahracky.cz']
    start_urls = [u'http://www.megahracky.cz/lego-stavebnice/']

    re_sku = re.compile('(\d\d\d?\d?\d?)')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@class="cat"]/li[not(@class)]/a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="boxit_new_cover"]')
        for product in products:
            loader = ProductLoader(selector=product, item=Product())
            url = product.select('div/a[@class="nadpisa"]/@href').extract()[0]
            identifier = url.replace('/', '').replace('.', '')
            loader.add_value('identifier', identifier)
            url = urljoin_rfc(base_url, url)
            name = product.select('div/a[@class="nadpisa"]/text()').extract()[0]

            loader.add_value('name', name)
            loader.add_value('url', url)
            loader.add_xpath('image_url', 'div/div[@class="boximages_new"]/div/a/img/@src')
            
            price = extract_price(product.select('div/div/div[@class="cenaa"]/text()').extract()[0])
            loader.add_value('price', price)
            loader.add_xpath('category', '//div/h1/text()')
            loader.add_value('sku', self.re_sku.findall(name))
            loader.add_value('brand', 'LEGO')
            if int(price) < 4000:
                loader.add_value('shipping_cost', 99)
            if price<=0:
                loader.add_value('stock', 0)
            yield self.load_item_with_metadata(loader.load_item())
