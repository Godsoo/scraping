# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
import re, time

from scrapy.utils.response import get_base_url
from urlparse import urljoin

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals


class ZalandoUkSpider(BaseSpider):

    name = "zalando_uk"
    start_urls = [
        "http://www.zalando.co.uk/ecco/",
        "http://www.zalando.co.uk/clarks/",
        "http://www.zalando.co.uk/dune/",
        "http://www.zalando.co.uk/bertie/"
    ]

    base_url = "http://www.zalando.co.uk"

    def __init__(self, *args, **kwargs):
      super(ZalandoUkSpider, self).__init__(*args, **kwargs)
      dispatcher.connect(self.spider_idle, signals.spider_idle)
      self._sale_premium_requests = []
      
    def spider_idle(self, spider):
      for request in self._sale_premium_requests:
	self._crawler.engine.crawl(request, self)
      
    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        categories = hxs.select("//ul[@class='catNav']//a")
        main_category = re.findall(re.compile("\.co\.uk\/(.+?)\/$"), response.url)[0].title()
        for category in categories:
            category_url = urljoin(response.url, category.select("./@href").extract()[0])
            category_name = category.select("./text()").extract()[0].replace('\"', '').strip()
            category_name_new = [main_category, category_name]
            request = Request(category_url, meta={'category': category_name_new}, callback=self.parse_category_01)
            if category_name.title() == "Kids":
	      yield request.replace(callback=self.parse_kids_category)
	    else:
	      yield request

    def parse_kids_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
	categories = hxs.select('//ul[@class="genderFilter"]//a')
	for category in categories:
            category_url = urljoin(response.url, category.select("./@href").extract()[0])
            category_name = category.select("./text()").extract()[0].replace('\"', '').strip()
            category_name_new = response.meta['category'] + [category_name]
            request = Request(category_url, meta={'category': category_name_new}, callback=self.parse_category_01)
            yield request

    def parse_category_01(self, response):

        hxs = HtmlXPathSelector(response)
        categories = hxs.select("//ul[@class='catNav']//a")
        for category in categories:
            category_url = urljoin(response.url, category.select("./@href").extract()[0])
            category_name = category.select("./text()").extract()[0].replace('\"', '').strip()
            category_name_new = response.meta['category'] + [category_name]
            request = Request(category_url, meta={'category': category_name_new}, callback=self.parse_category_02)
            if category_name.title() == 'Sale' or category_name.title() == 'Premium':
	      self._sale_premium_requests.append(request)
	    else:
	      yield request


    def parse_category_02(self, response):

        hxs = HtmlXPathSelector(response)
        categories = hxs.select("//ul[@class='catNav']//a")
        for category in categories:
            category_url = urljoin(response.url, category.select("./@href").extract()[0])
            category_name = category.select("./text()").extract()[0].replace('\"', '').strip()
            category_name = response.meta['category'] + [category_name]
            yield Request(category_url, meta={'category': category_name}, callback=self.parse_products)

        if not categories:
            yield Request(response.url, meta={'category': response.meta['category']}, callback=self.parse_products, dont_filter=True)


    def parse_products(self, response):

        hxs = HtmlXPathSelector(response)
        items = hxs.select("//li[@class='catalogArticlesList_item']")

        for item in items:

            l = {}

            l['name']       = ''.join(item.select(".//div[contains(@class,'articleName')]/text()").extract()).strip()
            l['url']        = self.base_url + item.select(".//a[contains(@class,'productBox')]/@href").extract()[0]
            l['image_url']  = item.select(".//img[contains(@class,'imageBoxImage')]/@src").extract()[0]
            l['stock']      = 0
            l['shipping']   = 0

            try:
                l['price']  = item.select(".//div[contains(@class,'priceBox')]//div[contains(@class,'specialPrice')]/text()").extract()[0].strip()
            except:
                l['price']  = item.select(".//div[contains(@class,'priceBox')]/div/text()").extract()[0].strip()

            if  l['price']:
                l['price']  = re.findall(re.compile('(\d+.\d*.\d*)'), l['price'])[0]
                l['stock']  = 1

            yield Request(url=l['url'], meta={'l': l, 'category': response.meta['category']}, callback=self.parse_item, dont_filter=True)

        try:
            next_page = hxs.select("//div[@class='catalogPagination']//a[contains(@class,'button-next')]/@href").extract()[0]
            next_page = self.base_url + next_page
            yield Request(url=next_page, callback=self.parse_products, meta=response.meta)
        except:
            pass



    def parse_item(self, response):

        hxs  = HtmlXPathSelector(response)
        item = response.meta['l']

        item['sku']        = hxs.select("//span[@itemprop='identifier']/@content").extract()[0].replace('sku:', '').strip()
        item['brand']      = hxs.select("//span[@itemprop='brand']/text()").extract()[0]
        item['identifier'] = item['sku']

        l = ProductLoader(item=Product(), response=response)

        l.add_value('name',          item['name'])
        l.add_value('image_url',     item['image_url'])
        l.add_value('url',           item['url'])
        l.add_value('price',         item['price'])
        l.add_value('stock',         item['stock'])
        l.add_value('brand',         item['brand'])
        l.add_value('identifier',    item['identifier'])
        l.add_value('sku',           item['sku'])
        l.add_value('shipping_cost', item['shipping'])

        for category in response.meta['category']:
            l.add_value('category', category)

        yield l.load_item()
