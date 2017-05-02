import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

import csv

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

HERE = os.path.abspath(os.path.dirname(__file__))

class BusDepotSpider(BaseSpider):
    name = 'busdepot.com'
    allowed_domains = ['busdepot.com']
    start_urls = ('http://www.busdepot.com/',)

    def __init__(self, *args, **kwargs):
        super(BusDepotSpider, self).__init__(*args, **kwargs)
        self.URLBASE = 'http://www.busdepot.com/'

        # parse the csv file to get the product ids
        csv_file = csv.reader(open(os.path.join(HERE, 'monitored_products.csv')))

        self.product_ids = [row[0] for row in csv_file]
        self.product_ids = self.product_ids[1:]
        self.product_ids = [re.sub('[\- \.]', '', product_id) for product_id in self.product_ids]

    def start_requests(self):
        url = 'http://www.busdepot.com'
        yield Request(url, callback=self.search_requests)

    def search_requests(self, response):
        for product_id in self.product_ids:
            form_name = 'search'
            form_data = {'q': product_id}
            form_request = FormRequest.from_response(response,
                                                     formname=form_name,
                                                     formdata=form_data,
                                                     dont_click=True,
                                                     dont_filter=True)
            form_request.meta['sku'] = product_id
            yield form_request

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//h2[@class="product-name"]/..')
        for product in products:
            try:
                href = product.select('.//h2/a/@href').extract()[0].strip()
                self.log('Request => %s' % href)
                yield Request(href, callback=self.parse_product, meta={'sku': response.meta['sku']})
            except IndexError:
                self.log('INDEX ERROR => %s' % response.url)
                continue
            else:
                return

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_xpath('name', '//div[@class="product-shop"]'
                                 '/div[@class="product-name"]/h1/text()')
        product_loader.add_value('sku', response.meta['sku'])
        product_loader.add_xpath('identifier', '//input[@name="product"]/@value')
        product_loader.add_xpath('image_url', '//div[@class="product-img-box"]//img/@src')
        product_loader.add_xpath('price',
                                 '//div[@class="price-box"]/span[contains(@id, "product-price-")]'
                                '/span[@class="price"]/text()')
        d_values = [d.strip() for d in hxs.select('//strong[contains(text(), '
                                                  '"Brand:")]/../text()').extract() if d.strip()]
        if d_values:
            d_labels = hxs.select('//strong[contains(text(), "Brand:")]/../strong/text()').extract()
            p_data = dict(zip(d_labels, d_values))
            if 'Brand:' in p_data:
                product_loader.add_value('brand', p_data['Brand:'])
        product_loader.add_xpath('category', '//div[@class="breadcrumbs"]//li[@class="product"]'
                                 '/preceding-sibling::li/a/text()')
        product_loader.add_value('url', response.url)

        yield product_loader.load_item()
