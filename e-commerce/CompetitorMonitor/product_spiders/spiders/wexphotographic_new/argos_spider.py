import urlparse
import os
import re
import json

from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from lib.schema import SpiderSchema

HERE = os.path.abspath(os.path.dirname(__file__))


class ArgosSpider(BaseSpider):
    name = 'wexphotographic_new-argos.co.uk'
    allowed_domains = ['argos.co.uk', 'argos.scene7.com']
    start_urls = [
        'http://www.argos.co.uk/static/Browse/ID72/33008331/c_1/1|category_root|Technology|33006169/c_2/2|cat_33006169|Cameras+and+camcorders|33008331.htm']

    rotate_agent = True

    def parse(self, response):
        # categories and subcategories
        for cat_href in response.xpath("//div[@id='categories']//li/a/@href").extract():
            yield Request(
                urlparse.urljoin(get_base_url(response), cat_href)
            )

        # promotional
        for promo_href in response.xpath("//div[@class='ss-row']//a[h2 and img]/@href").extract():
            yield Request(
                urlparse.urljoin(get_base_url(response), promo_href)
            )

        # products
        for product in response.xpath("//dl[@name]"):
            product_link = product.xpath(".//dd[contains(concat('',@class,''), 'image')]/a/@href").extract()[0]
            self.log(product_link)
            yield Request(
                product_link,
                callback=self.parse_product
            )

        # products next page
        for next_page in set(response.xpath("//a[@rel='next']/@href").extract()):
            yield Request(
                next_page
            )

        for product in self.parse_product(response):
            yield product

    def parse_product(self, response):
        url = response.url
        pdata = SpiderSchema(response).get_product()
        if not pdata:
            return

        options = response.xpath('//a[contains(@id, "pickerItem")]/@href').extract()
        for option in options:
            option_url = urlparse.urljoin(get_base_url(response), option)
            yield Request(option, callback=self.parse_product)

        l = ProductLoader(item=Product(), response=response)

        name = pdata['name']

        l.add_value('name', name)

        l.add_value('price', pdata['offers']['properties']['price'])

        sku = response.xpath("//li//text()[contains(., 'EAN')]").extract()
        if not sku:
            sku = response.xpath("//p//text()[contains(., 'EAN')]").re('EAN: (.*).')

        if sku:
            sku = sku[0].split(":")[-1].split('.')[0].strip()

            l.add_value('sku', sku)

        identifier = pdata['sku'].replace('/', '')
        l.add_value('identifier', identifier)

        l.add_value('category', SpiderSchema(response).get_category())

        product_image = response.css('li.active a img::attr(src)').extract_first()
        if product_image:
            l.add_value('image_url', response.urljoin(product_image))

        l.add_value('url', url)
        l.add_xpath('brand', '//*[@itemprop="brand"]/text()')
        product = l.load_item()

        if not product.get('image_url', None):
            image_url_req = 'http://argos.scene7.com/is/image/Argos?req=set,json&imageSet='+product['identifier']+'_R_SET'
            yield Request(image_url_req, callback=self.parse_image, meta={'product': product})
        else:
            yield product

    def parse_image(self, response):
        product = response.meta['product']
        image_url = re.findall('"img_set","n":"(.*)","item', response.body)
        if image_url:
            image_url = 'http://argos.scene7.com/is/image/' + image_url[0]
            product['image_url'] = image_url

        yield product
