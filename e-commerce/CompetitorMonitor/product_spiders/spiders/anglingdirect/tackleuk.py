import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.items import Product, ProductLoader


class TackleUkSpider(BaseSpider):
    name = 'tackleuk.co.uk'
    allowed_domains = ['tackleuk.co.uk']
    start_urls = ('https://www.tackleuk.co.uk/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # categories
        for url in hxs.select('//div[@id="top-menu"]//a/@href').extract():
            url = urljoin_rfc(base_url, url)
            url = add_or_replace_parameter(url, 'pageSize', '96')
            yield Request(url)

        # sub-categories
        for url in hxs.select('//div[@class="category-title"]/a/@href').extract():
            url = urljoin_rfc(base_url, url)
            url = add_or_replace_parameter(url, 'pageSize', '96')
            yield Request(url)

        # pages
        for url in hxs.select('//div[@class="pager"]//a/@href').extract():
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        products = [urljoin_rfc(base_url, url) for url in
                    hxs.select('//article[contains(@class, "product-grid-item")]//div[@class="product-name"]/a/@href').extract()]
        for url in products:
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        try:
            product_id = hxs.select('//form[@class="add-to-cart" or @id="add-notification"]/@action').re('productId=(.*)')[0]
        except:
            self.log('No product_id found on %s' %response.url)
            return

        image_url = hxs.select('//section[@id="product-image-viewer"]/div[@id="slider"]/ul[@class="slides"]//a[@class="fancy-box"]/@href').extract()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', product_id)
        loader.add_xpath('sku', '//p[contains(text(), "Brand Code")]/text()', re=r': (.*)$')
        loader.add_xpath('name', '//h1/text()')
        loader.add_xpath('price', '//span[@class="product-price"]/span/text()', re=r'[\d,.]+')
        if not loader.get_output_value('price'):
            loader.add_xpath('price', '//span[@class="product-price"]/span[@class="text-red"]/text()', re=r'[\d,.]+')
        loader.add_value('url', response.url)
        loader.add_xpath('category', '//nav[@id="breadcrumb"]/span/a/span/text()', lambda elms: elms[-1])
        loader.add_xpath('brand', '//a[@class="pull-right" and contains(@href, "Brands")]/img/@alt')
        out_of_stock = hxs.select('//div[@class="stock-status"]/span[@class="stock-status-circle out-of-stock"]')
        if out_of_stock:
            loader.add_value('stock', 0)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        item = loader.load_item()

        yield item

        data_model = hxs.select('//form[@class="add-to-cart"]/@data-model').extract()
        #import ipdb; ipdb.set_trace()
        if data_model:
            data = json.loads(data_model[0])
            if 'associatedProducts' in data:
                for option in data['associatedProducts']:
                    loader = ProductLoader(item=Product(item), response=response)
                    loader.replace_value('identifier', option['id'])
                    loader.replace_value('name', item['name'] + ' ' + ' '.join([o['value'].split(u'(\xa3')[0].strip() for o in option['fieldValues']]))
                    loader.replace_value('price', round(option['price'], 2))

                    yield loader.load_item()

