import os
import csv
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

HERE = os.path.abspath(os.path.dirname(__file__))


class CitizenWatchHutSpider(BaseSpider):
    name = 'citizen-thewatchhut.co.uk'
    allowed_domains = ['thewatchhut.co.uk']
    start_urls = ['http://www.thewatchhut.co.uk/']

    def start_requests(self):
        yield FormRequest('http://www.thewatchhut.co.uk/category-directory.asp', formdata={'change-currency': 'GB'})

    def parse(self, response):
        search_url = 'http://www.thewatchhut.co.uk/search/search.asp'
        with open(os.path.join(HERE, 'citizenproducts.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['SKU']
                yield FormRequest(
                    search_url,
                    formdata={'searchtext': row['SKU']},
                    dont_filter=True,
                    meta={'sku': row['SKU']},
                    callback=self.parse_search)

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        if re.search(r'Your search for .* was corrected to', response.body):
            return

        try:
            item_sel = hxs.select('//form[@class="product-form"]')[0]
        except:
            return
        loader = ProductLoader(item=Product(), selector=item_sel)
        loader.add_xpath('identifier', 'input[@name="productid"]/@value')
        loader.add_value('sku', response.meta['sku'])
        loader.add_xpath('name', 'a[@class="title"]/strong/text()')
        loader.add_xpath('url', 'a[@class="title"]/@href', lambda x: urljoin_rfc(base_url, x[0]))
        loader.add_value('brand', 'Citizen')
        loader.add_xpath('image_url', '../div[@class="details"]/@style', re=r"background-image:url\('(.*)'\);")

        price = ''.join(item_sel.select('div[@class="ourprice"]/span[1]//text()').extract())
        loader.add_value('price', price)

        stock = item_sel.select('div[contains(@class, "stock-status") and contains(@class, "in-stock")]')
        if not stock:
            loader.add_value('stock', 0)

        yield loader.load_item()
