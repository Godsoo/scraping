import csv
import os
import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class GiabriSpider(BaseSpider):
    name = 'newbricoman-giabri.it'
    allowed_domains = ['giabri.it']
    start_urls = ('http://www.giabri.it',)

    download_delay = 0

    def __init__(self, *args, **kwargs):
        super(GiabriSpider, self).__init__(*args, **kwargs)
        self.ean_codes = {}
        self.model_codes = {}
        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('EAN', None):
                    self.ean_codes[row['EAN']] = row['Code']
                if row.get('model', None):
                    self.model_codes[row['model'].lower()] = row['EAN']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        categories = hxs.select(u'//div[@id="categories"]//a/@href').extract()
        categories += hxs.select(u'//ul[@id="categoriesBoxes"]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(base_url, url)
            yield Request(url)
        pages = hxs.select(u'//div[@class="pages"][1]//a[not (contains(@class, "selectedPg"))]/@href').extract()
        for page_url in pages:
            url = urljoin_rfc(base_url, page_url)
            yield Request(url)
        for product in self.parse_product(response):
            yield product

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        products = hxs.select(u'//div[@class="resultBox"]')
        category = hxs.select(u'//div[@id="breadcrumbs"]/a/text()').extract()
        try:
            category = category[1].strip() if category else u''
        except:
            category = u''
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            url = product.select(u'./h2/a/@href')[0].extract()
            url = urljoin_rfc(get_base_url(response), url)
            loader.add_value('url', url)
            name = product.select(u'./h2/a/text()')[0].extract().strip()
            loader.add_value('name', name)
            loader.add_value('category', category)
            identifier = product.select(u'.//dt[contains(text(),"Cod. art")]/following-sibling::dd/text()')[0].extract()
            alternative_identifier = product.select(u'.//dt[contains(text(),"Codice Produttore")]/following-sibling::dd/text()').extract()
            if alternative_identifier:
                alternative_identifier = alternative_identifier[0].strip().replace(' ', '').replace('.', '')
            else:
                alternative_identifier = None
            loader.add_value('identifier', identifier)
            sku = product.select(u'.//dt[contains(text(),"Codice Produttore:")]/following-sibling::dd/text()')
            if sku:
                sku = sku[0].extract()
            else:
                sku = ''
            loader.add_value('sku', sku)
            try:
                brand = product.select(u'.//dt[starts-with(text(),"Produttore")]/following-sibling::dd/text()')[0].extract()
                loader.add_value('brand', brand)
            except:
                pass
            price = product.select(u'./ul/li[@class="price"]/h3[@class="mainPrice"]/text()')
            price = price[0].extract().replace('.', '').replace(',', '.') if price else '0.00'
            loader.add_value('price', price)
            image_url = product.select(u'.//img/@src').extract()
            if image_url:
                image_url = urljoin_rfc(base_url, image_url[0])
                loader.add_value('image_url', image_url)

            yield Request(url,
                          callback=self.parse_product_main,
                          meta={'loader': loader})

    def parse_product_main(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        shipping_url = urljoin_rfc(base_url,
                                   hxs.select('//div[@class="shippingDetails"]'
                                              '/a[@class="shippingDetailsButton"]/@href').extract()[0])

        shipping_url = add_or_replace_parameter(shipping_url, 'c', 'IT')
        shipping_url = add_or_replace_parameter(shipping_url, 'p', 'MI')
        shipping_url = add_or_replace_parameter(shipping_url, 'cap', '20100')

        yield Request(shipping_url,
                      callback=self.parse_shipping,
                      meta=response.meta)

    def parse_shipping(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = response.meta['loader']

        shipping = hxs.select('//tr[@class="bkg1"]/td/h4/text()').extract()
        if shipping:
            shipping_cost = shipping[0].replace('.', '').replace(',', '.')
            loader.add_value('shipping_cost', shipping_cost)

        yield loader.load_item()
