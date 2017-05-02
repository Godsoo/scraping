from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu as extract_price
import re
from scrapy.utils.url import add_or_replace_parameter

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals


class AlexanderandjamesDeSpider(BaseSpider):
    name = 'alexanderandjames.com_germany'
    allowed_domains = ['alexanderandjames.de']
    start_urls = ('http://www.alexanderandjames.de',)
    jar_counter = 0
    ids = []
    brands = []

    full_run_required = True

    def __init__(self, *args, **kwargs):
        super(AlexanderandjamesDeSpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if spider.name == self.name and self.full_run_required:
            self.full_run_required = False
            request = Request(self.start_urls[0], dont_filter=True, callback=self.parse_all_categories)
            self._crawler.engine.crawl(request, self)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse brands
        brands = hxs.select('//div[@class="categorymenu"]//ul[@class="brands brands_default"]//a/text()').extract()
        if brands:
            self.brands = brands[1:]
        else:
            self.brands = ["Alexander & James", "Bulleit", "Bushmills", "Cardhu", "Ciroc", "Clynelish", "Caol Ila",
                           "Cragganmore", "Dalwhinnie", "Don Julio", "Glen Elgin", "Glenkinchie", "Glenury Royal",
                           "Grand Marnier", "Johnnie Walker", "Ketel One", "Knockando", "Lagavulin", "Oban",
                           "Port Dundas", "Rosebank", "Royal Lochnagar", "Shui Jing Fang", "Talisker", "Tanqueray",
                           "Tekirdag", "Singleton", "Yeni Raki", "Zacapa"]
        # parse categories
        categories = hxs.select('//div[@class="categorymenu"]/ul/li[contains(@class, "staticMenuItem")]/a/text()').extract()
        urls = hxs.select('//div[@class="categorymenu"]/ul/li[contains(@class, "staticMenuItem")]/a/@href').extract()
        for category, url in zip(categories, urls):
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list, meta={'category': category})

    def parse_all_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[@class="categorymenu"]//a/text()').extract()
        urls = hxs.select('//div[@class="categorymenu"]//a/@href').extract()
        for category, url in zip(categories, urls):
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product_list,
                          meta={'category': category,
                                'full': True})

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        products = hxs.select('//div[contains(@class, "product producttile")]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            product_name = product.select('.//div[@class="name"]/a/text()').extract()
            if not product_name:
                continue
            else:
                product_name = product_name[0].strip()
            image_url = product.select('.//img[@id="firimg"]/@src').extract()[0]
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            product_loader.add_value('name', product_name)
            url = product.select('.//div[@class="name"]/a/@href').extract()[0]
            product_loader.add_value('url', url)
            match = re.search(r"(\d+)\.html", url)
            if match:
                identifier = match.group(1)
                if identifier in self.ids:
                    continue
                else:
                    self.ids.append(identifier)
            else:
                continue
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('sku', identifier)
            price = product.select('.//div[@class="salesprice"]/text()').extract()[0]
            product_loader.add_value('price', extract_price(price))
            category = response.meta.get('category', '')
            if not category or response.meta.get('full'):
                category2 = product.select('.//div[@class="capacityType"]/text()').extract()
                if category2:
                    category2 = category2[0].split(u'\u2022')
                    if len(category2) > 1:
                        category2 = category2[1]
                    else:
                        category2 = category2[0]
                    if category2.strip():
                        category = category2
            if category:
                # Diageo have requested that we group all categories with 'Whisky' or 'Whiskey' in the name into one category named 'Whisky'
                # https://www.assembla.com/spaces/competitormonitor/tickets/2254
                if 'whisky' in category.lower() or 'whiskey' in category.lower():
                    category = 'Whisky'
                product_loader.add_value('category', category.strip())
            for brand in self.brands:
                if brand in product_name.replace('A&J', 'Alexander & James').replace(u'C\xeeroc', 'Ciroc'):
                    product_loader.add_value('brand', brand)
                    break
            product = product_loader.load_item()
            self.jar_counter += 1
            yield Request(url,
                          callback=self.parse_product,
                          meta={'product': product, 'cookiejar': self.jar_counter},
                          cookies={})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product = response.meta['product']
        stock = hxs.select('//span[@class="isinstock"]/text()').re(r"(\d+)")
        if stock:
            product['stock'] = int(stock[0])
        url = '/on/demandware.store/Sites-alexanderandjamesEU-Site/de_DE/Cart-MiniAddProduct'
        url = urljoin_rfc(base_url, url)
        url = add_or_replace_parameter(url, 'pid', str(product['identifier']))
        url = add_or_replace_parameter(url, 'Quantity', '1')
        yield Request(url,
                      dont_filter=True,
                      meta={'product': product, 'cookiejar': response.meta['cookiejar']},
                      callback=self.parse_shipping_price1)

    def parse_shipping_price1(self, response):
        base_url = get_base_url(response)
        url = '/on/demandware.store/Sites-alexanderandjamesEU-Site/de_DE/Cart-Show'
        url = urljoin_rfc(base_url, url)
        yield Request(url,
                      dont_filter=True,
                      meta={'product': response.meta['product'], 'cookiejar': response.meta['cookiejar']},
                      callback=self.parse_shipping_price2)

    @staticmethod
    def parse_shipping_price2(response):
        hxs = HtmlXPathSelector(response)
        product = response.meta['product']
        shipping = hxs.select('//tr[@class="ordershipping"]/td[2]/span/text()').extract()
        if shipping:
            shipping = extract_price(shipping[0])
            shipping_discount = hxs.select('//tr[@class="ordershippingdiscount discount"]/td[2]/span/text()').extract()
            if shipping_discount:
                shipping -= extract_price(shipping_discount[0])
            product['shipping_cost'] = shipping
        yield product