# -*- coding: utf-8 -*-
import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc

HERE = os.path.abspath(os.path.dirname(__file__))


class FunAgainSpider(BaseSpider):
    name = u'lego_usa_funagain_com'
    allowed_domains = ['www.funagain.com']
    start_urls = [
        u'https://www.funagain.com/control/catalogsearch?&search_query=lego&search_operator=AND&list_type=list&view_index=0&show_unavailable=Y&view_size=1000#pagecontent',
    ]
    errors = []

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'funagain_map_deviation.csv')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products list
        urls = hxs.select('//*[@id="catalogsearch_body_keyword"]//div[@class="productsummaryrow"]//div[@class="prodsummarydesc"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//div[@id="prodtitle"]/h1/text()').extract()[0].strip()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        image_url = hxs.select('//div[@id="productheaderimage"]/a[2]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin(base_url, image_url[0]))
        price = hxs.select('//span[@id="prodpriceyourprice"]/text()').extract()
        if price:
            loader.add_value('price', extract_price(price[0]))
        else:
            loader.add_value('price', 0)
        identifier = hxs.select('//input[@name="product_id"]/@value').extract()[0]
        loader.add_value('identifier', identifier.strip())
        available = hxs.select('//div[@id="prodinstock"]').extract()
        if not available:
            loader.add_value('stock', 0)
        loader.add_value('brand', 'LEGO')
        yield loader.load_item()
