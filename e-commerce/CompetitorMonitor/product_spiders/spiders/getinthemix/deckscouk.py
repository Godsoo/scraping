import re
from copy import copy
import time

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from productloader import load_product
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import FormRequest

class DecksCoUk(BaseSpider):
    name = 'decks.co.uk'
    allowed_domains = ['decks.co.uk']
    start_urls = ('http://www.decks.co.uk',)

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url)

        # Parse search
        yield Request('http://www.decks.co.uk/search.aspx?KEY=%25',
                      callback=self.parse_category)

    def parse_options(self, response):
        base_url = 'http://www.decks.co.uk'
        loader = response.meta.get('loader')
        hxs = HtmlXPathSelector(response)

        image_url = hxs.select('//div[@id="lrgImageWrap"]//img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        category = hxs.select('//div[@id="productCategoryTrail"]/p/a/text()').extract()
        if category:
            for c in category:
                loader.add_value('category', c.strip())

        options = hxs.select('//table[@class="choice-table"]/tr[contains(@id,"_rowChoice")]')
        options = options if len(options) > 1 else []
        i = 0
        for option in options:
            loader = copy(loader)

            price = option.select('./td[contains(@class,"td_price")]/strong/text()').re('([\d\.,]+)')
            if price:
                price = price[0].strip().replace(',', '')

            shipping_cost = '0.00' if float(price if price else loader.get_output_value('price')) >= 50.00 else '4.99'
            loader.add_value('shipping_cost', shipping_cost)

            stock = option.select('.//td[contains(@class,"td_stock")]/text()').extract()[0]
            if '**DISCONTINUED**' in stock:
                continue
            if not('In Stock' in stock or 'days' in stock):
                loader.add_value('stock', 0)
            p = loader.load_item()
            p['name'] = ' '.join(option.select('./td[contains(@class,"td_name")]//text()').extract()).strip()
            if price:
                p['price'] = price
            p['identifier'] += '.%d' % i
            yield p
            i += 1
        if not options:
            price = loader.get_output_value('price')
            price = price if price else '0.0'
            shipping_cost = '0.00' if float(price) >= 50.00 else '4.99'
            loader.add_value('shipping_cost', shipping_cost)
            stock = hxs.select('//div[@id="details"]//td[contains(@class,"td_stock")]/text()').extract()[0]
            if '**DISCONTINUED**' in stock:
                return
            if not('In Stock' in stock or 'days' in stock):
                loader.add_value('stock', 0)
            yield loader.load_item()

    def parse_product(self, response):
        base_url = 'http://www.decks.co.uk'

        hxs = HtmlXPathSelector(response)

        retry = False

        products = hxs.select('//div[@id="search-results"]/ul/li')
        for p in products:
            loader = ProductLoader(item=Product(), selector=hxs)
            name = p.select('.//h2/a/text()')[0].extract()
            url = p.select('.//h2/a/@href')[0].extract()
            url = urljoin_rfc(base_url, url)
            try:
                price = p.select('.//h3[@class="price"]/strong/text()').re('\xa3(.*)')[0]
            except:
                retry = True
                break
            loader.add_value('url', url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            identifier = '_'.join(p.select('.//p[@class="add"]/a[contains(@href, ":AddToBasket")]/@href').re(r'(\d+)'))
            if identifier:
                loader.add_value('identifier', identifier)
                yield Request(url, callback=self.parse_options, meta={'loader': loader})

        if retry:
            retry = int(response.meta.get('retry', 0))
            if retry < 200:
                retry += 1
                self.log('>>> Retrying No. %s => %s' % (str(retry), response.url))
                time.sleep(60)
                meta = response.meta.copy()
                meta['retry'] = retry
                yield Request(response.url,
                              meta=meta,
                              dont_filter=True)


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # category_urls = hxs.select('//div[@class="products-nav"]/ul/li/a/@href').extract()
        category_urls = hxs.select('//div[@id="left"]//a[contains(@href, "products")]/@href').extract()
        for url in category_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url, self.parse_category)


    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # subcategories (for categories that don't show the products directly)
        subcategories_urls = hxs.select('//ul[@class="smaller"]//p[@class="go"]/a/@href').extract()
        for url in subcategories_urls:
           url = urljoin_rfc(base_url, url)
           yield Request(url, callback=self.parse_category)

        # products
        products = [p for p in self.parse_product(response)]
        for p in products:
            yield p

        # next page
        next_page = hxs.select('//a[contains(text(),"Next")]/@href').extract()
        if next_page and products:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(url, callback=self.parse_category)

