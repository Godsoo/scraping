import re
import urllib2

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader


class SevenOaksSpider(BaseSpider):
    name = 'sevenoakssoundandvision.co.uk'
    allowed_domains = ['www.store.sevenoakssoundandvision.co.uk', 'store.sevenoakssoundandvision.co.uk',
                       'sevenoakssoundandvision.co.uk']
    start_urls = ('http://www.sevenoakssoundandvision.co.uk/c-2-HIFI_Audio.aspx',)

    def __init__(self, *args, **kwargs):
        super(SevenOaksSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select('//div[@class="subcats"]/a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        # pages
        # next_pages = hxs.select(u'//a[contains(text(),"Next")]/@href').extract()
        # for next_page in next_pages:
        #    url = urljoin_rfc(get_base_url(response), next_page)
        #    yield Request(url)

        # products
        # for product in self.parse_product(response):
        #    yield product
        products = re.findall('u":"\\\(.*?)",', response.body)
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        identifier = hxs.select('//input[contains(@name, "ProductID")]/@value').extract()
        if not identifier:
            identifier = re.search('p-(\d+)-', response.url).group(1)
        else:
            identifier = identifier[0]

        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        name = ' '.join(hxs.select('//div[@class="product-title"]/text()').extract()).strip()
        loader.add_value('name', name)
        price = hxs.select(u'//div[contains(@id, "' + identifier + '")]/div/div[@class="standardNowPrice"]/text()').extract()
        if not price:
            price = hxs.select(u'//div[contains(@id, "' + identifier + '")]/div/div[@class="saleNowPrice"]/text()').extract()
        if not price:
             price = hxs.select(u'//div[@class="product-price"]//div[@class="saleNowPrice"]/span/text()').extract()

        loader.add_value('price', price[0])
        yield loader.load_item()
