import os
import csv
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc
from product_spiders.items import ProductLoader, Product

HERE = os.path.abspath(os.path.dirname(__file__))
CSV_FILENAME = os.path.join(os.path.dirname(__file__), 'cheapmowers.csv')


class cheapmowersSpider(BaseSpider):
    name = "cheapmowers.com"
    allowed_domains = ["www.cheapmowers.com"]
    start_urls = (
        "http://www.cheapmowers.com/acatalog/sitemap.html",)

    def __init__(self, *args, **kwargs):
        super(cheapmowersSpider, self).__init__(*args, **kwargs)
        self.names = {}
        with open(CSV_FILENAME) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.names[row['url']] = row['name'].decode('utf-8', 'ignore')

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        try:
            name = hxs.select(".//h1/text()").extract()[0].strip()
        except:
            return

        name = name.replace(u'\u00ae', u'')
        url = response.url
        price = hxs.select(".//div[@class='product-details']//span[@class='product-price']/span/text()").re(r'\xa3([\.0-9,]*)')
        if not price:
            return

        price = price[0]

        out_of_stock = hxs.select('//span/span/strong[contains(text(), "SOLD OUT")]')
        

        category = hxs.select('//p[@class="text_breadcrumbs"]/a/text()').extract()[-1]
        brand = hxs.select('//p[@class="text_breadcrumbs"]/a/text()').extract()[-2]

        image_url = hxs.select('//img[contains(@id, "im-")]/@src').extract()
        image_url = urljoin_rfc('http://www.cheapmowers.com/acatalog/', image_url[0]) if image_url else ''
        if name:
            l = ProductLoader(item=Product(), response=response)
            l.add_value('name', self.names.get(url, name))
            l.add_xpath('identifier', '//input[@name="SID"]/@value')
            l.add_value('url', url)
            l.add_value('image_url', image_url)
            l.add_value('brand', brand)
            l.add_value('category', category)
            l.add_value('price', price)
            if out_of_stock:
                l.add_value('stock', 0)
            yield l.load_item()
