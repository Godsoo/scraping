from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader

try:
    import json
except ImportError:
    import simplejson as json


class FastenalSpider(BaseSpider):
    name = "fastenal"
    allowed_domains = ["fastenal.com"]
    start_urls = (
        'http://www.fastenal.com/web/products/fasteners/hardware/flashing-products/_/Navigation?term=&termca=&termpx=&sortby=webrank&sortdir=descending&searchmode=productSearch&rfqXref=&rfqKeyword=&rfqId=&rfqLineId=&r=~|categoryl1:%22600000%20Fasteners%22|~%20~|categoryl2:%22600206%20Hardware%22|~%20~|categoryl3:%22600213%20Flashing%20Products%22|~',
        )

    def parse(self, response):
        base_url = get_base_url(response)

        hxs = HtmlXPathSelector(response)

        next_page = hxs.select('//a[contains(@title, "Next Page")]/@href').extract()

        if next_page:
            next_url = next_page[0]
            yield Request(urljoin_rfc(base_url, next_url), callback=self.parse)

        items = hxs.select('//div[@id="attribute-table"]//div[@class="row"]'
                           '//div[@class="title"]/a/@href').extract()
        for item in items:
            yield Request(urljoin_rfc(base_url, item), callback=self.parse_item)

    def parse_item(self, response):
        hxs = HtmlXPathSelector(response)

        title = hxs.select('//h1[@class="header active"]/text()').extract()
        url = response.url
        price = hxs.select('//form[@id="ProductAddForm"]//dd[@class="wholesale"]/text()').extract().pop().strip()

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', str(title))
        l.add_value('name', title)
        l.add_value('url', url)
        l.add_value('price', price)
        return l.load_item()
