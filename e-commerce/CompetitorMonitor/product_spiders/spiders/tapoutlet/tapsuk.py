import re
import json
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from phantomjs import PhantomJS


class TapsUKSpider(BaseSpider):
    name = 'tapsuk.com'
    allowed_domains = ['tapsuk.com']
    start_urls = ['http://www.tapsuk.com/search/all-products?sort=1&show=240']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for product in hxs.select('//div[@class="product_details"]//a[@class="product_title"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product)

        for page in hxs.select('//div[@class="pages"]//a[@class="page_num"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@id="breadcrumb_container"]//a/text()').extract()
        if categories:
            category = categories[-1]
        else:
            category = None

        name = hxs.select('//div[@id="overview_tab_content"]/h2/text()').extract()
        if name:
            name = name[0].strip()
        if not name:
            name = hxs.select('//title/text()').extract()[0].split('-')
            name = name[0:-1] if len(name) > 1 else name
            name = '-'.join(name).strip()

        sku = hxs.select('//span[@id="product_reference"]/text()').extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('identifier', '//span[@id="product_reference"]/text()')
        loader.add_value('url', response.url)
        loader.add_value('name', name.strip())
        if sku:
            loader.add_value('sku', sku[0].replace(' ', ''))
        price = hxs.select('//div[@id="product_price"]//span[@id="product_price_sale"]'
                           '//span[@class="price"]//span[@class="ex"]//span[@class="GBP"]/text()').extract()
        price = re.sub(u'[^\d\.]', u'', price[0].strip())
        # loader.add_value('price', str(round(Decimal(price) / Decimal(1.2), 2)))
        loader.add_value('price', price)
        if category:
            loader.add_value('category', category)

        img = hxs.select('//img[@id="product_medium_image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))
        brand = hxs.select('//div[@id="product_page_brand"]/a/@title').extract()
        brand = brand[0] if brand else ''
        loader.add_value('brand', brand)

        item = loader.load_item()

        if not item['identifier'] or item['identifier'].strip() == 'n/a':
            browser = PhantomJS.create_browser()
            self.log('>>> BROWSER: GET => response.url')
            browser.get(response.url)
            self.log('BROWSER: OK!')
            hxs = HtmlXPathSelector(browser.page_source)
            browser.quit()

            item['identifier'] = hxs.select('//span[@id="product_reference"]/text()').extract()[0].strip()

        yield item
