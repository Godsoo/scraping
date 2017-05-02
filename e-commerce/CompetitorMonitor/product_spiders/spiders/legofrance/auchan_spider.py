import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu

class AuchanSpider(BaseSpider):
    name = 'legofrance-auchan.fr'
    allowed_domains = ['auchan.fr']
    start_urls = ('http://www.auchan.fr/jeux--jouets/construction/lego/achat2/6860409',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//div[contains(@class, "productContainer")]/div[contains(@class, "product ")]/div/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next_page = hxs.select('//div[contains(@class, "pagination")]/ul/li/a[@class="next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        name = hxs.select('//div[@id="productDetailUpdateable"]//h1[@class="BdCn wide"]/text()').extract()[0]
        desc = hxs.select('//div[@id="productDetailUpdateable"]//div[@class="pdp_subtitle mb-10"]/div/text()').extract()
        desc = desc[0] if desc else ''
        #identifier = hxs.select('//input[@name="productCodePost"]/@value').extract().pop()
        identifier = response.url.split('/')[-1].split('-')[1]
        sku = re.findall(r'\d+', name) or [""]

        full_name = name + ' ' + desc
        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', identifier.upper())
        l.add_value('name', full_name.strip())
        try:
            l.add_value('category', hxs.select('//div[@id="breadcrumb"]/ul/li/a/text()').extract().pop())
        except:
            l.add_value('category', '')
        l.add_value('brand', 'LEGO')
        l.add_value('sku', sku)
        l.add_value('url', response.url)
        l.add_xpath('price', '//meta[@itemprop="price"]/@content')
        l.add_xpath('image_url', '//div[@id="primary_image"]/a/img/@src')
        yield l.load_item()
