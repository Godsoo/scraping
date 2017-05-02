import csv
import os
import copy
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class BoscovsSpider(BaseSpider):

    name = 'legousa-boscovs.com'
    allowed_domains = ['boscovs.com']
    start_urls = [
        'https://www.boscovs.com/ast/lego',
    ]

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'boscovs_map_deviation.csv')

    _re_sku = re.compile('(\d\d\d\d\d?)')

    def parse(self, response):
        from scrapy.utils.response import open_in_browser
        open_in_browser(response)
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//*[contains(@id,"left_menu")]//li/a')
        categories = []
        for category in categories:
            category_url = add_or_replace_parameter(urljoin_rfc(base_url,
                                                                category.select('./@href').extract()[0].strip()),
                                                    'pageLimit', '120')
            yield Request(category_url, meta={'category': category.select('./text()').extract()[0].strip()})

        pages = response.css('a.pageselectorlink::attr(href)').extract()
        for page in pages:
            yield Request(page)

        products = hxs.select('//div[contains(@class, "prod_title")]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product),
                          callback=self.parse_product,
                          meta=response.meta)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        identifier = hxs.select('//div[@id="itemNumber"]/@data-bos-itemnumber').extract()[0]

        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()

        sku = self._re_sku.findall(name)
        sku = sku[0] if sku else ''

        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('brand', 'LEGO')
        loader.add_value('category', response.meta.get('category'))
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)

        price = hxs.select("//div[@id='prodTotal']/text()").extract()
        if not price:
            price = hxs.select('//div[@class="span-9b clearfix pad-2 center fleft"]//span[@class="red bold m-large"]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="span-9b clearfix pad-2 center fleft"]//span[@class="dark-blue"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="prodPrice" and @itemprop="price"][1]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="prodPrice"][1]/text()').extract()

        price = price[0] if price else ''
        loader.add_value('price', price)
        loader.add_xpath('image_url', '//img[@class="vertical-top subpend-2"]/@src')
        yield loader.load_item()
