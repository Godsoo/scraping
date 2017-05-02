from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu
from scrapy.http import Request
import re
import json

import time
import datetime

class Heaven4kidsDkSpider(BaseSpider):
    name = 'heaven4kids.dk'
    allowed_domains = ['heaven4kids.dk']
    start_urls = ('http://www.heaven4kids.dk/maerker/Lego/products',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        urls = hxs.select('//div[@class="brandfocusSubCats"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url))

        ajax_url = 'http://www.heaven4kids.dk/eurostores_dev/ajax/LoadProducts.php?'\
            'rand=%(rand)s&folderName=ajax&fileName=LoadProducts&currentPageNumber=1'\
            '&productLimit=9999&pageType=manufacturer&sortID=3&genderID=null&onSale=0'\
            '&manufacturerID=%(man_id)s&categoryId=all&_=%(rand)s'

        params = {'man_id': hxs.select('//input[@id="manufacturerID"]/@value').extract()[0],
                  'rand': self._get_rand()}

        yield Request(ajax_url % params,
                      callback=self.parse_products, dont_filter=True, meta={'base_url': base_url})

    def parse_products(self, response):

        data = json.loads(response.body)

        hxs = HtmlXPathSelector(text=data['products'])
        base_url = response.meta.get('base_url')

        products = hxs.select('//div[contains(@class, "productItem")]')
        for product in products:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            identifier = product.select('.//*[contains(@id, "main_image")]/@id').re(r'(\d+)$')
            if not identifier:
                continue
            product_loader.add_value('identifier', identifier[0])
            image_url = product.select('.//img[contains(@id, "main_image")]/@data-src').extract()[0]
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            product_name = product.select('.//span[contains(@class, "productTitle")]/a/text()').extract()[0]
            product_loader.add_value('name', product_name)
            sku = ''
            for match in re.finditer(r"([\d,\.]+)", product_name):
                if len(match.group()) > len(sku):
                    sku = match.group()
            product_loader.add_value('sku', sku)
            url = product.select('.//span[contains(@class, "productTitle")]/a/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            price = ''.join(product.select('.//span[@class="price"]/text()').re(r'[\d.,]+'))
            price = extract_price_eu(price)
            product_loader.add_value('price', price)

            yield product_loader.load_item()

    def _get_rand(self):
        return str(int(time.mktime(datetime.datetime.utcnow().timetuple()) * 1000))
